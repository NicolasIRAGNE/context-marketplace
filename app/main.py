from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import httpx
import asyncio
import sys
from typing import List, Optional

from app.config import get_settings, Settings
from app.models import (
    CreateContextRequest, UpdateContextRequest, CreateContextFileRequest, 
    UpdateContextFileRequest, Context, ContextFile
)
from app.services import GitHubService, context_service

app = FastAPI(title="Context Marketplace")
settings = get_settings()

# Session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# OAuth setup
oauth = OAuth()
oauth.register(
    name='github',
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    authorize_url='https://github.com/login/oauth/authorize',
    access_token_url='https://github.com/login/oauth/access_token',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email repo read:org'},
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


async def get_current_user(request: Request):
    """Get current user from session"""
    user = request.session.get('user')
    return user


def require_auth(user=Depends(get_current_user)):
    """Require authentication"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def get_github_service(user=Depends(require_auth)) -> GitHubService:
    """Get GitHub service for current user"""
    return GitHubService(user['access_token'])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user=Depends(get_current_user)):
    """Home page"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user": user}
    )


@app.get("/login")
async def login(request: Request):
    """Initiate GitHub OAuth login"""
    redirect_uri = f"{settings.app_url}/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)


@app.get("/callback")
async def callback(request: Request):
    """GitHub OAuth callback"""
    try:
        token = await oauth.github.authorize_access_token(request)
        
        # Get user info from GitHub
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                'https://api.github.com/user',
                headers={
                    'Authorization': f'token {token["access_token"]}',
                    'Accept': 'application/json'
                }
            )
            user_data = resp.json()
            
            # Get user email if not public
            if not user_data.get('email'):
                email_resp = await client.get(
                    'https://api.github.com/user/emails',
                    headers={
                        'Authorization': f'token {token["access_token"]}',
                        'Accept': 'application/json'
                    }
                )
                emails = email_resp.json()
                primary_email = next((e['email'] for e in emails if e['primary']), None)
                user_data['email'] = primary_email
        
        # Store user in session
        request.session['user'] = {
            'id': user_data['id'],
            'login': user_data['login'],
            'name': user_data.get('name'),
            'email': user_data.get('email'),
            'avatar_url': user_data['avatar_url'],
            'access_token': token['access_token']
        }
        
        return RedirectResponse(url='/')
        
    except Exception as e:
        print(f"OAuth error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")


@app.get("/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    return RedirectResponse(url='/')


@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, user=Depends(get_current_user)):
    """User profile page"""
    if not user:
        return RedirectResponse(url='/login')
    
    # Get user's contexts
    user_contexts = context_service.get_user_contexts(user['id'])
    
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "user": user, "contexts": user_contexts}
    )


# Context Management API Routes

@app.post("/api/contexts")
async def create_context(
    request: CreateContextRequest,
    user=Depends(require_auth),
    github_service: GitHubService = Depends(get_github_service)
):
    """Create a new context"""
    try:
        context = context_service.create_context(
            user_id=user['id'],
            user_login=user['login'],
            request=request
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # If GitHub repo URL provided, fetch repo info
    if request.github_repo_url:
        repo_info = await github_service.get_repo_info(request.github_repo_url)
        if repo_info:
            context_service.set_context_repo(context.id, repo_info)
            
            # Get contributors
            contributors = await github_service.get_contributors(repo_info.owner, repo_info.name)
            context_service.set_context_contributors(context.id, contributors)
    
    # Generate default files
    context_service.generate_default_files(context.id, github_service)
    
    return context_service.get_context(context.id)


@app.get("/api/contexts")
async def list_contexts(user=Depends(get_current_user)):
    """List contexts (user's own + public ones)"""
    if user:
        user_contexts = context_service.get_user_contexts(user['id'])
        public_contexts = [ctx for ctx in context_service.get_public_contexts() if ctx.owner_id != user['id']]
        return {"user_contexts": user_contexts, "public_contexts": public_contexts}
    else:
        return {"user_contexts": [], "public_contexts": context_service.get_public_contexts()}


@app.get("/api/contexts/{context_id}")
async def get_context(context_id: str, user=Depends(get_current_user)):
    """Get a specific context"""
    context = context_service.get_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    # Check access permissions
    if not context.is_public and (not user or user['id'] != context.owner_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return context


@app.put("/api/contexts/{context_id}")
async def update_context(
    context_id: str,
    request: UpdateContextRequest,
    user=Depends(require_auth)
):
    """Update a context"""
    context = context_service.get_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    if user['id'] != context.owner_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    updated_context = context_service.update_context(context_id, request)
    return updated_context


@app.delete("/api/contexts/{context_id}")
async def delete_context(context_id: str, user=Depends(require_auth)):
    """Delete a context"""
    context = context_service.get_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    if user['id'] != context.owner_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = context_service.delete_context(context_id)
    return {"success": success}


@app.post("/api/contexts/{context_id}/files")
async def create_context_file(
    context_id: str,
    request: CreateContextFileRequest,
    user=Depends(require_auth)
):
    """Add a file to a context"""
    context = context_service.get_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    if user['id'] != context.owner_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    file_obj = context_service.add_file_to_context(context_id, request)
    return file_obj


@app.put("/api/contexts/{context_id}/files/{file_name}")
async def update_context_file(
    context_id: str,
    file_name: str,
    request: UpdateContextFileRequest,
    user=Depends(require_auth)
):
    """Update a file in a context"""
    context = context_service.get_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    if user['id'] != context.owner_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    file_obj = context_service.update_context_file(context_id, file_name, request)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    
    return file_obj


@app.delete("/api/contexts/{context_id}/files/{file_name}")
async def delete_context_file(
    context_id: str,
    file_name: str,
    user=Depends(require_auth)
):
    """Delete a file from a context"""
    context = context_service.get_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    if user['id'] != context.owner_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = context_service.remove_file_from_context(context_id, file_name)
    return {"success": success}


@app.get("/api/user/repositories-with-contexts")
async def get_user_repositories_with_contexts(
    user=Depends(require_auth),
    github_service: GitHubService = Depends(get_github_service)
):
    """Get user's repositories and mark which ones have contexts"""
    try:
        async with httpx.AsyncClient() as client:
            all_repos = []
            
            # 1. Get user's personal repositories
            page = 1
            while len(all_repos) < 200:  # Reasonable limit
                repos_resp = await client.get(
                    'https://api.github.com/user/repos',
                    headers=github_service.headers,
                    params={
                        'sort': 'updated',
                        'per_page': 100,
                        'type': 'all',
                        'page': page
                    }
                )
                
                if repos_resp.status_code != 200:
                    break
                
                repos_page = repos_resp.json()
                if not repos_page:
                    break
                    
                all_repos.extend(repos_page)
                page += 1
            
            # 2. Get user's organizations and their repos
            orgs_resp = await client.get(
                'https://api.github.com/user/orgs',
                headers=github_service.headers,
                params={'per_page': 100}
            )
            
            if orgs_resp.status_code == 200:
                orgs = orgs_resp.json()
                
                for org in orgs:
                    org_login = org['login']
                    org_page = 1
                    while True:
                        org_repos_resp = await client.get(
                            f'https://api.github.com/orgs/{org_login}/repos',
                            headers=github_service.headers,
                            params={
                                'sort': 'updated',
                                'per_page': 100,
                                'type': 'all',
                                'page': org_page
                            }
                        )
                        
                        if org_repos_resp.status_code != 200:
                            break
                            
                        org_repos = org_repos_resp.json()
                        if not org_repos:
                            break
                            
                        existing_ids = {repo['id'] for repo in all_repos}
                        new_org_repos = [repo for repo in org_repos if repo['id'] not in existing_ids]
                        all_repos.extend(new_org_repos)
                        
                        org_page += 1
                        if len(new_org_repos) < 100:
                            break
            
            # 3. Format repositories
            formatted_repos = []
            repo_urls = []
            for repo in all_repos:
                permissions = repo.get('permissions', {})
                
                formatted_repo = {
                    'id': repo['id'],
                    'name': repo['name'],
                    'full_name': repo['full_name'],
                    'description': repo.get('description'),
                    'html_url': repo['html_url'],
                    'clone_url': repo['clone_url'],
                    'private': repo['private'],
                    'language': repo.get('language'),
                    'updated_at': repo['updated_at'],
                    'stargazers_count': repo['stargazers_count'],
                    'forks_count': repo['forks_count'],
                    'fork': repo.get('fork', False),
                    'owner_type': repo['owner']['type'],
                    'owner_login': repo['owner']['login'],
                    'permissions': {
                        'admin': permissions.get('admin', False),
                        'push': permissions.get('push', False),
                        'pull': permissions.get('pull', True)
                    },
                    'has_context': False,  # Will be updated below
                    'context_id': None     # Will be updated below
                }
                formatted_repos.append(formatted_repo)
                repo_urls.append(repo['html_url'])
            
            # 4. Check which repositories have contexts
            repo_contexts = context_service.get_contexts_for_repos(user['id'], repo_urls)
            for repo in formatted_repos:
                if repo['html_url'] in repo_contexts:
                    repo['has_context'] = True
                    repo['context_id'] = repo_contexts[repo['html_url']]
            
            # Sort by updated date (most recent first)
            formatted_repos.sort(key=lambda x: x['updated_at'], reverse=True)
            
            return formatted_repos
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"GitHub API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching repositories: {str(e)}")


@app.get("/api/user/repositories")
async def get_user_repositories(github_service: GitHubService = Depends(get_github_service)):
    """Get all repositories the user has access to (owned, collaborator, organization)"""
    try:
        async with httpx.AsyncClient() as client:
            all_repos = []
            
            # 1. Get user's personal repositories
            print("Fetching user repos...")
            page = 1
            while len(all_repos) < 200:  # Reasonable limit
                repos_resp = await client.get(
                    'https://api.github.com/user/repos',
                    headers=github_service.headers,
                    params={
                        'sort': 'updated',
                        'per_page': 100,
                        'type': 'all',  # owner, collaborator, organization_member
                        'page': page
                    }
                )
                
                if repos_resp.status_code != 200:
                    break
                
                repos_page = repos_resp.json()
                if not repos_page:  # No more repos
                    break
                    
                all_repos.extend(repos_page)
                page += 1
            
            # 2. Get user's organizations
            print("Fetching user orgs...")
            orgs_resp = await client.get(
                'https://api.github.com/user/orgs',
                headers=github_service.headers,
                params={'per_page': 100}
            )
            
            if orgs_resp.status_code == 200:
                orgs = orgs_resp.json()
                print(f"Found {len(orgs)} organizations")
                
                # 3. Get repositories for each organization
                for org in orgs:
                    org_login = org['login']
                    print(f"Fetching repos for org: {org_login}")
                    
                    org_page = 1
                    while True:
                        org_repos_resp = await client.get(
                            f'https://api.github.com/orgs/{org_login}/repos',
                            headers=github_service.headers,
                            params={
                                'sort': 'updated',
                                'per_page': 100,
                                'type': 'all',  # all, public, private, forks, sources, member
                                'page': org_page
                            }
                        )
                        
                        if org_repos_resp.status_code != 200:
                            break
                            
                        org_repos = org_repos_resp.json()
                        if not org_repos:
                            break
                            
                        # Filter out repos already in our list (user might be owner of org repo)
                        existing_ids = {repo['id'] for repo in all_repos}
                        new_org_repos = [repo for repo in org_repos if repo['id'] not in existing_ids]
                        all_repos.extend(new_org_repos)
                        
                        org_page += 1
                        
                        # Limit per org to avoid too many repos
                        if len(new_org_repos) < 100:
                            break
            
            print(f"Total repos found: {len(all_repos)}")
            
            # Filter and format repositories
            filtered_repos = []
            for repo in all_repos:
                # Get permissions for the user
                permissions = repo.get('permissions', {})
                
                filtered_repos.append({
                    'id': repo['id'],
                    'name': repo['name'],
                    'full_name': repo['full_name'],
                    'description': repo.get('description'),
                    'html_url': repo['html_url'],
                    'clone_url': repo['clone_url'],
                    'private': repo['private'],
                    'language': repo.get('language'),
                    'updated_at': repo['updated_at'],
                    'stargazers_count': repo['stargazers_count'],
                    'forks_count': repo['forks_count'],
                    'fork': repo.get('fork', False),
                    'owner_type': repo['owner']['type'],  # User or Organization
                    'owner_login': repo['owner']['login'],
                    'permissions': {
                        'admin': permissions.get('admin', False),
                        'push': permissions.get('push', False),
                        'pull': permissions.get('pull', True)
                    }
                })
            
            # Sort by updated date (most recent first)
            filtered_repos.sort(key=lambda x: x['updated_at'], reverse=True)
            
            print(f"Returning {len(filtered_repos)} filtered repos")
            return filtered_repos
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"GitHub API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching repositories: {str(e)}")


@app.post("/api/contexts/{context_id}/contributors/{login}/toggle")
async def toggle_contributor_selection(
    context_id: str,
    login: str,
    user=Depends(require_auth)
):
    """Toggle contributor selection for people.md generation"""
    context = context_service.get_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    if user['id'] != context.owner_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Find and toggle the contributor
    contributor_found = False
    for contrib in context.contributors:
        if contrib.login == login:
            contrib.selected = not contrib.selected
            contributor_found = True
            break
    
    if not contributor_found:
        raise HTTPException(status_code=404, detail="Contributor not found")
    
    # Save the context with updated contributor selection
    context_service._save_context(context)
    
    # Regenerate people.md in real-time
    people_content = context_service._generate_people_content(context)
    updated_file = context_service.update_context_file(
        context_id,
        "people.md",
        UpdateContextFileRequest(content=people_content)
    )
    
    # Return the updated context with the new file content
    updated_context = context_service.get_context(context_id)
    
    return {
        "context": updated_context,
        "updated_file": updated_file,
        "contributor_login": login,
        "contributor_selected": next((c.selected for c in updated_context.contributors if c.login == login), False)
    }


@app.post("/api/contexts/{context_id}/create-pr")
async def create_pull_request(
    context_id: str,
    user=Depends(require_auth),
    github_service: GitHubService = Depends(get_github_service)
):
    """Create a pull request with context files on the target repository"""
    context = context_service.get_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    if not context.github_repo:
        raise HTTPException(status_code=400, detail="Context is not connected to a GitHub repository")
    
    # Check if user has write access to the repository
    try:
        repo_info = await github_service.get_repo_info(context.github_repo.url)
        if not repo_info:
            raise HTTPException(status_code=404, detail="Repository not found or not accessible")
        
        # Create the PR using GitHub service
        pr_url = await github_service.create_context_pr(
            owner=repo_info.owner,
            repo=repo_info.name,
            context=context,
            user_login=user['login']
        )
        
        return {"pr_url": pr_url}
        
    except Exception as e:
        print(f"Error creating PR: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating pull request: {str(e)}")


# Web UI Routes

@app.get("/repositories", response_class=HTMLResponse)
async def repositories_page(request: Request, user=Depends(require_auth)):
    """Repositories listing page"""
    return templates.TemplateResponse(
        "repositories.html",
        {"request": request, "user": user}
    )


@app.get("/contexts", response_class=HTMLResponse)
async def contexts_page(request: Request, user=Depends(get_current_user)):
    """Contexts listing page"""
    return templates.TemplateResponse(
        "contexts.html",
        {"request": request, "user": user}
    )


@app.get("/contexts/new", response_class=HTMLResponse)
async def new_context_page(request: Request, user=Depends(require_auth)):
    """New context creation page"""
    return templates.TemplateResponse(
        "new_context.html",
        {"request": request, "user": user}
    )


@app.get("/contexts/{context_id}", response_class=HTMLResponse)
async def context_detail_page(
    request: Request,
    context_id: str,
    user=Depends(get_current_user)
):
    """Context detail page"""
    context = context_service.get_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    # Check access permissions
    if not context.is_public and (not user or user['id'] != context.owner_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    can_edit = user and user['id'] == context.owner_id
    
    return templates.TemplateResponse(
        "context_detail.html",
        {
            "request": request,
            "user": user,
            "context": context,
            "can_edit": can_edit
        }
    )


@app.get("/contexts/{context_id}/edit", response_class=HTMLResponse)
async def edit_context_page(
    request: Request,
    context_id: str,
    user=Depends(require_auth)
):
    """Context editing page"""
    context = context_service.get_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    if user['id'] != context.owner_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return templates.TemplateResponse(
        "edit_context.html",
        {"request": request, "user": user, "context": context}
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Context Marketplace")
    parser.add_argument("--mcp", action="store_true", help="Run as MCP server instead of web server")
    parser.add_argument("--host", default=settings.host, help="Host to bind to")
    parser.add_argument("--port", type=int, default=settings.port, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", default=settings.debug, help="Enable auto-reload")
    
    args = parser.parse_args()
    
    if args.mcp:
        # Run MCP server
        from app.mcp_server import run_mcp_server
        base_url = f"http://{args.host}:{args.port}"
        asyncio.run(run_mcp_server(base_url))
    else:
        # Run web server
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload
        )