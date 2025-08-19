#!/usr/bin/env python3
"""
MCP Server for Context Marketplace
Provides programmatic access to code contexts via the Model Context Protocol
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urljoin
import httpx

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    CallToolRequest,
    ListResourcesRequest,
    ListToolsRequest,
    ReadResourceRequest,
)
from pydantic import BaseModel, Field

from app.services import context_service


class ContextMarketplaceMCPServer:
    """MCP Server for Context Marketplace"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.server = Server("context-marketplace")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List all available context resources"""
            try:
                # Use the local context service instead of HTTP
                all_contexts = list(context_service.contexts.values())
                
                resources = []
                
                for context in all_contexts:
                    if context.is_public:  # Only show public contexts or implement auth
                        resources.append(Resource(
                            uri=f"context://{context.id}",
                            name=f"Context: {context.name}",
                            description=context.description or 'Code context',
                            mimeType="application/json"
                        ))
                        
                        # Add individual files as resources
                        for file in context.files:
                            resources.append(Resource(
                                uri=f"context://{context.id}/files/{file.name}",
                                name=f"{context.name}/{file.name}",
                                description=f"File from context: {context.name}",
                                mimeType="text/plain"
                            ))
                
                return resources
            except Exception as e:
                print(f"Error listing resources: {e}", file=sys.stderr)
                return []
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a specific context resource"""
            try:
                if not uri.startswith("context://"):
                    raise ValueError(f"Invalid URI scheme: {uri}")
                
                path = uri[10:]  # Remove "context://" prefix
                
                if "/files/" in path:
                    # Reading a specific file
                    context_id, file_path = path.split("/files/", 1)
                    
                    context = context_service.get_context(context_id)
                    if not context:
                        raise ValueError(f"Context not found: {context_id}")
                    
                    # Find the specific file
                    for file in context.files:
                        if file.name == file_path:
                            return file.content
                    
                    raise ValueError(f"File not found: {file_path}")
                else:
                    # Reading entire context
                    context_id = path
                    
                    context = context_service.get_context(context_id)
                    if not context:
                        raise ValueError(f"Context not found: {context_id}")
                    
                    # Format context as readable text
                    output = f"# Context: {context.name}\\n\\n"
                    
                    if context.description:
                        output += f"**Description:** {context.description}\\n\\n"
                    
                    output += f"**Owner:** @{context.owner_login}\\n"
                    output += f"**Files:** {len(context.files)}\\n"
                    output += f"**Public:** {'Yes' if context.is_public else 'No'}\\n\\n"
                    
                    if context.github_repo:
                        repo = context.github_repo
                        output += f"**GitHub Repository:** {repo.full_name}\\n"
                        if repo.description:
                            output += f"**Repo Description:** {repo.description}\\n"
                        output += "\\n"
                    
                    # Add all files content
                    output += "## Files\\n\\n"
                    for file in context.files:
                        output += f"### {file.name}\\n\\n"
                        output += f"```\\n{file.content}\\n```\\n\\n"
                    
                    return output
            
            except Exception as e:
                print(f"Error reading resource {uri}: {e}", file=sys.stderr)
                raise
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="search_contexts",
                    description="Search for contexts by name or description",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for context name or description"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_context_details",
                    description="Get detailed information about a specific context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "context_id": {
                                "type": "string",
                                "description": "ID of the context to retrieve"
                            }
                        },
                        "required": ["context_id"]
                    }
                ),
                Tool(
                    name="list_contexts",
                    description="List all available contexts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "public_only": {
                                "type": "boolean",
                                "description": "Whether to show only public contexts",
                                "default": True
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_context_files",
                    description="Get all files from a specific context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "context_id": {
                                "type": "string",
                                "description": "ID of the context"
                            }
                        },
                        "required": ["context_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            try:
                if name == "search_contexts":
                    return await self._search_contexts(arguments["query"])
                
                elif name == "get_context_details":
                    return await self._get_context_details(arguments["context_id"])
                
                elif name == "list_contexts":
                    public_only = arguments.get("public_only", True)
                    return await self._list_contexts(public_only)
                
                elif name == "get_context_files":
                    return await self._get_context_files(arguments["context_id"])
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _search_contexts(self, query: str) -> List[TextContent]:
        """Search for contexts"""
        try:
            all_contexts = list(context_service.contexts.values())
            
            # Simple text search
            query_lower = query.lower()
            matching_contexts = []
            
            for context in all_contexts:
                if not context.is_public:  # Skip private contexts
                    continue
                    
                name_match = query_lower in context.name.lower()
                desc_match = context.description and query_lower in context.description.lower()
                
                if name_match or desc_match:
                    matching_contexts.append(context)
            
            if matching_contexts:
                result = f"Found {len(matching_contexts)} contexts matching '{query}':\\n\\n"
                for context in matching_contexts:
                    result += f"**{context.name}** (ID: {context.id})\\n"
                    if context.description:
                        result += f"  Description: {context.description}\\n"
                    result += f"  Owner: @{context.owner_login}\\n"
                    result += f"  Files: {len(context.files)}\\n"
                    result += f"  Public: {'Yes' if context.is_public else 'No'}\\n\\n"
                
                return [TextContent(type="text", text=result)]
            else:
                return [TextContent(type="text", text=f"No contexts found matching '{query}'")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error searching contexts: {str(e)}")]
    
    async def _get_context_details(self, context_id: str) -> List[TextContent]:
        """Get detailed context information"""
        try:
            context = context_service.get_context(context_id)
            if not context:
                return [TextContent(type="text", text=f"Context not found: {context_id}")]
            
            if not context.is_public:
                return [TextContent(type="text", text=f"Context is private: {context_id}")]
            
            result = f"# Context: {context.name}\\n\\n"
            result += f"**ID:** {context.id}\\n"
            
            if context.description:
                result += f"**Description:** {context.description}\\n"
            
            result += f"**Owner:** @{context.owner_login}\\n"
            result += f"**Public:** {'Yes' if context.is_public else 'No'}\\n"
            result += f"**Created:** {context.created_at}\\n"
            result += f"**Updated:** {context.updated_at}\\n\\n"
            
            if context.github_repo:
                repo = context.github_repo
                result += f"**GitHub Repository:** {repo.full_name}\\n"
                if repo.description:
                    result += f"**Repo Description:** {repo.description}\\n"
                if repo.language:
                    result += f"**Primary Language:** {repo.language}\\n"
                result += "\\n"
            
            result += f"## Files ({len(context.files)})\\n\\n"
            for file in context.files:
                result += f"- **{file.name}** ({file.file_type.value})\\n"
                if len(file.content) > 200:
                    result += f"  Preview: {file.content[:200]}...\\n"
                else:
                    result += f"  Content: {file.content}\\n"
                result += "\\n"
            
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting context details: {str(e)}")]
    
    async def _list_contexts(self, public_only: bool) -> List[TextContent]:
        """List all contexts"""
        try:
            all_contexts = list(context_service.contexts.values())
            
            if public_only:
                contexts = [ctx for ctx in all_contexts if ctx.is_public]
            else:
                contexts = all_contexts
            
            if contexts:
                result = f"Found {len(contexts)} contexts:\\n\\n"
                
                for context in contexts:
                    result += f"**{context.name}** (ID: {context.id})\\n"
                    if context.description:
                        result += f"  Description: {context.description}\\n"
                    result += f"  Owner: @{context.owner_login}\\n"
                    result += f"  Files: {len(context.files)}\\n"
                    result += f"  Public: {'Yes' if context.is_public else 'No'}\\n"
                    
                    if context.github_repo:
                        result += f"  Repository: {context.github_repo.full_name}\\n"
                    
                    result += "\\n"
                
                return [TextContent(type="text", text=result)]
            else:
                return [TextContent(type="text", text="No contexts found")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing contexts: {str(e)}")]
    
    async def _get_context_files(self, context_id: str) -> List[TextContent]:
        """Get all files from a context"""
        try:
            context = context_service.get_context(context_id)
            if not context:
                return [TextContent(type="text", text=f"Context not found: {context_id}")]
            
            if not context.is_public:
                return [TextContent(type="text", text=f"Context is private: {context_id}")]
            
            if not context.files:
                return [TextContent(type="text", text=f"No files found in context: {context.name}")]
            
            result = f"# Files from Context: {context.name}\\n\\n"
            
            for file in context.files:
                result += f"## {file.name} ({file.file_type.value})\\n\\n"
                result += f"```\\n{file.content}\\n```\\n\\n"
            
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting context files: {str(e)}")]
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="context-marketplace",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )


async def run_mcp_server(base_url: str = "http://localhost:8000"):
    """Run the MCP server"""
    server = ContextMarketplaceMCPServer(base_url=base_url)
    await server.run()