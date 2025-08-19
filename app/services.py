import httpx
import uuid
import os
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from app.models import (
    Context, ContextFile, GitHubRepo, GitHubContributor, 
    ContextFileType, CreateContextRequest, UpdateContextRequest,
    CreateContextFileRequest, UpdateContextFileRequest, GenerateFileRequest
)


class GitHubService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/json'
        }
    
    async def get_repo_info(self, repo_url: str) -> Optional[GitHubRepo]:
        """Extract repo info from GitHub URL and fetch details"""
        try:
            # Parse GitHub URL to get owner/repo
            match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$', repo_url)
            if not match:
                return None
            
            owner, repo = match.groups()
            
            async with httpx.AsyncClient() as client:
                # Get repository details
                repo_resp = await client.get(
                    f'https://api.github.com/repos/{owner}/{repo}',
                    headers=self.headers
                )
                
                if repo_resp.status_code != 200:
                    return None
                
                repo_data = repo_resp.json()
                
                # Get languages
                lang_resp = await client.get(
                    f'https://api.github.com/repos/{owner}/{repo}/languages',
                    headers=self.headers
                )
                languages = lang_resp.json() if lang_resp.status_code == 200 else {}
                
                return GitHubRepo(
                    owner=repo_data['owner']['login'],
                    name=repo_data['name'],
                    full_name=repo_data['full_name'],
                    description=repo_data.get('description'),
                    url=repo_data['html_url'],
                    clone_url=repo_data['clone_url'],
                    default_branch=repo_data['default_branch'],
                    language=repo_data.get('language'),
                    languages=languages
                )
        except Exception as e:
            print(f"Error fetching repo info: {e}")
            return None
    
    async def get_contributors(self, owner: str, repo: str) -> List[GitHubContributor]:
        """Get repository contributors"""
        try:
            async with httpx.AsyncClient() as client:
                contributors_resp = await client.get(
                    f'https://api.github.com/repos/{owner}/{repo}/contributors',
                    headers=self.headers
                )
                
                if contributors_resp.status_code != 200:
                    return []
                
                contributors_data = contributors_resp.json()
                contributors = []
                
                for contrib in contributors_data[:10]:  # Limit to top 10 contributors
                    # Get detailed user info
                    user_resp = await client.get(
                        contrib['url'],
                        headers=self.headers
                    )
                    
                    user_data = user_resp.json() if user_resp.status_code == 200 else {}
                    
                    contributors.append(GitHubContributor(
                        login=contrib['login'],
                        id=contrib['id'],
                        avatar_url=contrib['avatar_url'],
                        name=user_data.get('name'),
                        email=user_data.get('email'),
                        bio=user_data.get('bio'),
                        pronouns=user_data.get('pronouns'),
                        company=user_data.get('company'),
                        website=user_data.get('blog'),  # GitHub API uses 'blog' for website
                        location=user_data.get('location'),
                        twitter_username=user_data.get('twitter_username'),
                        public_repos=user_data.get('public_repos'),
                        followers=user_data.get('followers'),
                        following=user_data.get('following'),
                        created_at=user_data.get('created_at'),
                        hireable=user_data.get('hireable'),
                        contributions=contrib['contributions']
                    ))
                
                return contributors
        except Exception as e:
            print(f"Error fetching contributors: {e}")
            return []
    
    async def get_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """Get content of a specific file from the repository"""
        try:
            async with httpx.AsyncClient() as client:
                file_resp = await client.get(
                    f'https://api.github.com/repos/{owner}/{repo}/contents/{path}',
                    headers=self.headers
                )
                
                if file_resp.status_code != 200:
                    return None
                
                file_data = file_resp.json()
                
                if file_data.get('type') != 'file':
                    return None
                
                import base64
                content = base64.b64decode(file_data['content']).decode('utf-8')
                return content
        except Exception as e:
            print(f"Error fetching file content: {e}")
            return None
    
    async def create_context_pr(self, owner: str, repo: str, context, user_login: str) -> str:
        """Create a pull request with context files"""
        try:
            import base64
            import json
            from datetime import datetime
            
            async with httpx.AsyncClient() as client:
                # Get the default branch
                repo_resp = await client.get(
                    f'https://api.github.com/repos/{owner}/{repo}',
                    headers=self.headers
                )
                
                if repo_resp.status_code != 200:
                    raise Exception("Could not access repository")
                
                repo_data = repo_resp.json()
                default_branch = repo_data['default_branch']
                
                # Get the latest commit SHA from default branch
                ref_resp = await client.get(
                    f'https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{default_branch}',
                    headers=self.headers
                )
                
                if ref_resp.status_code != 200:
                    raise Exception("Could not get default branch reference")
                
                latest_sha = ref_resp.json()['object']['sha']
                
                # Create a new branch for the PR
                branch_name = f"context-{context.name.lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                
                create_ref_resp = await client.post(
                    f'https://api.github.com/repos/{owner}/{repo}/git/refs',
                    headers=self.headers,
                    json={
                        'ref': f'refs/heads/{branch_name}',
                        'sha': latest_sha
                    }
                )
                
                if create_ref_resp.status_code != 201:
                    raise Exception("Could not create branch")
                
                # Create .context directory and files
                files_to_create = []
                for file in context.files:
                    file_path = f".context/{file.name}"
                    files_to_create.append({
                        'path': file_path,
                        'content': file.content
                    })
                
                # Create each file in the .context directory
                for file_info in files_to_create:
                    content_encoded = base64.b64encode(file_info['content'].encode('utf-8')).decode('utf-8')
                    
                    create_file_resp = await client.put(
                        f'https://api.github.com/repos/{owner}/{repo}/contents/{file_info["path"]}',
                        headers=self.headers,
                        json={
                            'message': f'Add {file_info["path"]} from context marketplace',
                            'content': content_encoded,
                            'branch': branch_name
                        }
                    )
                    
                    if create_file_resp.status_code not in [201, 200]:
                        print(f"Warning: Could not create file {file_info['path']}")
                
                # Create the pull request
                pr_title = f"Add project context from {context.name}"
                pr_body = f"""This PR adds project context files from the Context Marketplace.

**Context:** {context.name}
{f"**Description:** {context.description}" if context.description else ""}

## Files Added:
{chr(10).join([f"- `.context/{file.name}`" for file in context.files])}

## What is this?
These files contain project context information including:
- Technology stack and architecture
- Business logic and requirements  
- Team information and contributors
- Development guidelines and standards

The `.context/` directory helps new contributors understand the project quickly and provides context for AI tools and code assistants.

---
*Created by @{user_login} via [Context Marketplace]()*
"""
                
                pr_resp = await client.post(
                    f'https://api.github.com/repos/{owner}/{repo}/pulls',
                    headers=self.headers,
                    json={
                        'title': pr_title,
                        'body': pr_body,
                        'head': branch_name,
                        'base': default_branch
                    }
                )
                
                if pr_resp.status_code != 201:
                    error_data = pr_resp.json()
                    raise Exception(f"Could not create PR: {error_data.get('message', 'Unknown error')}")
                
                pr_data = pr_resp.json()
                return pr_data['html_url']
                
        except Exception as e:
            print(f"Error creating PR: {e}")
            raise Exception(f"Failed to create pull request: {str(e)}")


class ContextService:
    def __init__(self):
        # In production, this would use a proper database
        self.contexts: Dict[str, Context] = {}
        self.contexts_dir = Path("contexts")
        self.contexts_dir.mkdir(exist_ok=True)
    
    def create_context(self, user_id: int, user_login: str, request: CreateContextRequest) -> Context:
        """Create a new context"""
        # Check if context already exists for this repo and user
        if request.github_repo_url:
            existing_context = self.get_context_by_repo_url(user_id, request.github_repo_url)
            if existing_context:
                raise ValueError(f"Context already exists for repository: {request.name}")
        
        context_id = str(uuid.uuid4())
        
        context = Context(
            id=context_id,
            name=request.name,
            description=request.description,
            owner_id=user_id,
            owner_login=user_login,
            is_public=request.is_public
        )
        
        self.contexts[context_id] = context
        self._save_context(context)
        
        return context
    
    def get_context(self, context_id: str) -> Optional[Context]:
        """Get a context by ID"""
        return self.contexts.get(context_id)
    
    def get_user_contexts(self, user_id: int) -> List[Context]:
        """Get all contexts for a user"""
        return [ctx for ctx in self.contexts.values() if ctx.owner_id == user_id]
    
    def get_public_contexts(self) -> List[Context]:
        """Get all public contexts"""
        return [ctx for ctx in self.contexts.values() if ctx.is_public]
    
    def get_context_by_repo_url(self, user_id: int, repo_url: str) -> Optional[Context]:
        """Get context by repository URL for a specific user"""
        for context in self.contexts.values():
            if (context.owner_id == user_id and 
                context.github_repo and 
                context.github_repo.url == repo_url):
                return context
        return None
    
    def get_contexts_for_repos(self, user_id: int, repo_urls: List[str]) -> Dict[str, str]:
        """Get context IDs for a list of repository URLs"""
        repo_contexts = {}
        for context in self.contexts.values():
            if (context.owner_id == user_id and 
                context.github_repo and 
                context.github_repo.url in repo_urls):
                repo_contexts[context.github_repo.url] = context.id
        return repo_contexts
    
    def update_context(self, context_id: str, request: UpdateContextRequest) -> Optional[Context]:
        """Update a context"""
        context = self.contexts.get(context_id)
        if not context:
            return None
        
        if request.name is not None:
            context.name = request.name
        if request.description is not None:
            context.description = request.description
        if request.is_public is not None:
            context.is_public = request.is_public
        
        context.updated_at = datetime.now()
        self._save_context(context)
        
        return context
    
    def delete_context(self, context_id: str) -> bool:
        """Delete a context"""
        if context_id in self.contexts:
            del self.contexts[context_id]
            self._delete_context_files(context_id)
            return True
        return False
    
    def add_file_to_context(self, context_id: str, request: CreateContextFileRequest) -> Optional[ContextFile]:
        """Add a file to a context"""
        context = self.contexts.get(context_id)
        if not context:
            return None
        
        file_obj = ContextFile(
            name=request.name,
            file_type=request.file_type,
            content=request.content
        )
        
        # Remove existing file with same name
        context.files = [f for f in context.files if f.name != request.name]
        context.files.append(file_obj)
        
        context.updated_at = datetime.now()
        self._save_context(context)
        
        return file_obj
    
    def update_context_file(self, context_id: str, file_name: str, request: UpdateContextFileRequest) -> Optional[ContextFile]:
        """Update a file in a context"""
        context = self.contexts.get(context_id)
        if not context:
            return None
        
        for file_obj in context.files:
            if file_obj.name == file_name:
                file_obj.content = request.content
                file_obj.updated_at = datetime.now()
                
                context.updated_at = datetime.now()
                self._save_context(context)
                
                return file_obj
        
        return None
    
    def remove_file_from_context(self, context_id: str, file_name: str) -> bool:
        """Remove a file from a context"""
        context = self.contexts.get(context_id)
        if not context:
            return False
        
        original_count = len(context.files)
        context.files = [f for f in context.files if f.name != file_name]
        
        if len(context.files) < original_count:
            context.updated_at = datetime.now()
            self._save_context(context)
            return True
        
        return False
    
    def set_context_repo(self, context_id: str, github_repo: GitHubRepo) -> Optional[Context]:
        """Set the GitHub repository for a context"""
        context = self.contexts.get(context_id)
        if not context:
            return None
        
        context.github_repo = github_repo
        context.updated_at = datetime.now()
        self._save_context(context)
        
        return context
    
    def set_context_contributors(self, context_id: str, contributors: List[GitHubContributor]) -> Optional[Context]:
        """Set the contributors for a context"""
        context = self.contexts.get(context_id)
        if not context:
            return None
        
        context.contributors = contributors
        context.updated_at = datetime.now()
        self._save_context(context)
        
        return context
    
    def _save_context(self, context: Context):
        """Save context to file (in production, would save to database)"""
        context_dir = self.contexts_dir / context.id
        context_dir.mkdir(exist_ok=True)
        
        # Save context metadata
        with open(context_dir / "metadata.json", "w") as f:
            f.write(context.model_dump_json(indent=2))
        
        # Save individual files
        files_dir = context_dir / "files"
        files_dir.mkdir(exist_ok=True)
        
        for file_obj in context.files:
            with open(files_dir / file_obj.name, "w") as f:
                f.write(file_obj.content)
    
    def _delete_context_files(self, context_id: str):
        """Delete context files from disk"""
        import shutil
        context_dir = self.contexts_dir / context_id
        if context_dir.exists():
            shutil.rmtree(context_dir)
    
    def generate_default_files(self, context_id: str, github_service: Optional[GitHubService] = None) -> Optional[Context]:
        """Generate default context files"""
        context = self.contexts.get(context_id)
        if not context:
            return None
        
        # Generate stack.md
        stack_content = self._generate_stack_content(context, github_service)
        self.add_file_to_context(context_id, CreateContextFileRequest(
            name="stack.md",
            file_type=ContextFileType.STACK,
            content=stack_content
        ))
        
        # Generate business.md
        business_content = self._generate_business_content(context)
        self.add_file_to_context(context_id, CreateContextFileRequest(
            name="business.md",
            file_type=ContextFileType.BUSINESS,
            content=business_content
        ))
        
        # Generate people.md
        people_content = self._generate_people_content(context)
        self.add_file_to_context(context_id, CreateContextFileRequest(
            name="people.md",
            file_type=ContextFileType.PEOPLE,
            content=people_content
        ))
        
        # Generate guidelines.md
        guidelines_content = self._generate_guidelines_content(context, github_service)
        self.add_file_to_context(context_id, CreateContextFileRequest(
            name="guidelines.md",
            file_type=ContextFileType.GUIDELINES,
            content=guidelines_content
        ))
        
        return self.contexts.get(context_id)
    
    def _generate_stack_content(self, context: Context, github_service: Optional[GitHubService]) -> str:
        """Generate stack.md content"""
        content = "# Technology Stack\n\n"
        
        if context.github_repo and context.github_repo.languages:
            content += "## Languages\n"
            for lang in sorted(context.github_repo.languages.keys()):
                content += f"- **{lang}**\n"
            content += "\n"
        
        content += "## Frameworks & Libraries\n"
        content += "_Add frameworks and libraries used in this project_\n\n"
        
        content += "## Tools & Services\n"
        content += "_Add development tools, CI/CD, and services used_\n\n"
        
        content += "## Architecture\n"
        content += "_Describe the high-level architecture of the project_\n"
        
        return content
    
    def _generate_business_content(self, context: Context) -> str:
        """Generate business.md content"""
        content = "# Business Logic\n\n"
        
        if context.github_repo and context.github_repo.description:
            content += f"## Project Description\n{context.github_repo.description}\n\n"
        
        content += "## Core Features\n"
        content += "_List the main features and functionality_\n\n"
        
        content += "## Business Rules\n"
        content += "_Document important business rules and constraints_\n\n"
        
        content += "## User Stories\n"
        content += "_Add key user stories and use cases_\n"
        
        return content
    
    def _generate_people_content(self, context: Context) -> str:
        """Generate people.md content"""
        content = "# People\n\n"
        
        if context.contributors:
            content += "## Contributors\n"
            for contrib in context.contributors:
                if contrib.selected:
                    content += f"### {contrib.name or contrib.login}\n"
                    content += f"- **GitHub**: [@{contrib.login}](https://github.com/{contrib.login})\n"
                    
                    if contrib.pronouns:
                        content += f"- **Pronouns**: {contrib.pronouns}\n"
                    
                    if contrib.bio:
                        content += f"- **Bio**: {contrib.bio}\n"
                    
                    if contrib.company:
                        content += f"- **Company**: {contrib.company}\n"
                    
                    if contrib.location:
                        content += f"- **Location**: {contrib.location}\n"
                    
                    if contrib.website:
                        # Clean up the website URL
                        website = contrib.website
                        if not website.startswith(('http://', 'https://')):
                            website = f"https://{website}"
                        content += f"- **Website**: [{contrib.website}]({website})\n"
                    
                    if contrib.email:
                        content += f"- **Email**: {contrib.email}\n"
                    
                    if contrib.twitter_username:
                        content += f"- **Twitter**: [@{contrib.twitter_username}](https://twitter.com/{contrib.twitter_username})\n"
                    
                    
                    if contrib.hireable:
                        content += f"- **Available for hire**: Yes\n"
                    
                    
                    content += "\n"
        
        content += "## Team Roles\n"
        content += "_Define roles and responsibilities_\n\n"
        
        content += "## Contact Information\n"
        content += "_Add relevant contact information_\n"
        
        return content
    
    def _generate_guidelines_content(self, context: Context, github_service: Optional[GitHubService]) -> str:
        """Generate guidelines.md content"""
        content = "# Development Guidelines\n\n"
        
        # Try to get CONTRIBUTING.md from the repository
        contributing_content = None
        if context.github_repo and github_service:
            try:
                # This would be an async call in practice
                contributing_content = "# See CONTRIBUTING.md in the repository"
            except:
                pass
        
        if contributing_content:
            content += "## Contributing Guidelines\n"
            content += contributing_content + "\n\n"
        else:
            content += "## Code Style\n"
            content += "_Define coding standards and style guidelines_\n\n"
            
            content += "## Development Workflow\n"
            content += "_Describe the development process and workflow_\n\n"
            
            content += "## Testing Guidelines\n"
            content += "_Document testing requirements and practices_\n\n"
            
            content += "## Review Process\n"
            content += "_Define the code review process_\n"
        
        return content


# Global service instances (in production, would use dependency injection)
context_service = ContextService()