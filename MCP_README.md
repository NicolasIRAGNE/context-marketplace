# Context Marketplace MCP Server

This repository includes a Model Context Protocol (MCP) server that provides programmatic access to code contexts for Large Language Models like Claude.

## What is MCP?

The Model Context Protocol (MCP) is an open standard that enables AI assistants to access external data sources and tools. The Context Marketplace MCP server allows Claude and other AI models to:

- Browse and search available code contexts
- Read context files and metadata
- List user repositories from GitHub
- Create new contexts from GitHub repositories

## Features

### Resources
The MCP server exposes contexts and their files as resources:
- `context://{context_id}` - Full context with all files
- `context://{context_id}/files/{filename}` - Individual files

### Tools
Available tools for AI interactions:

1. **search_contexts** - Search for contexts by name or description
2. **get_context_details** - Get detailed information about a specific context
3. **list_user_repositories** - List GitHub repositories accessible to the user
4. **create_context_from_repo** - Create a new context from a GitHub repository

## Installation

### Docker (Recommended)

The MCP server is included in the docker-compose setup:

```bash
# Start both the web app and MCP server
docker-compose up

# The MCP server will be available for stdio communication
# Web app: http://localhost:8000
# MCP server: Available via stdio in the mcp-server container
```

### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r mcp_requirements.txt
```

2. Start the Context Marketplace web application:
```bash
python -m app.main
```

3. Start the MCP server:
```bash
python -m app.main --mcp
```

## Configuration

### Environment Variables

- `CONTEXT_MARKETPLACE_URL` - URL of the Context Marketplace API (default: http://localhost:8000)

### Claude Desktop Integration

To use the MCP server with Claude Desktop, add this to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "context-marketplace": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "context-marketplace-mcp-server-1",
        "python",
        "-m",
        "app.main",
        "--mcp"
      ]
    }
  }
}
```

Alternatively, if running manually:

```json
{
  "mcpServers": {
    "context-marketplace": {
      "command": "python",
      "args": ["-m", "app.main", "--mcp"],
      "cwd": "/path/to/context-marketplace"
    }
  }
}
```

## Usage Examples

Once configured, you can interact with the Context Marketplace through Claude:

### Searching for Contexts
```
Claude, search for contexts related to "React" in the context marketplace.
```

### Creating a Context from a Repository
```
Claude, create a new context from my GitHub repository https://github.com/username/my-project
```

### Browsing Repositories
```
Claude, show me my GitHub repositories and which ones have contexts created.
```

### Reading Context Files
```
Claude, show me the stack.md file from the context with ID "abc123"
```

## API Integration

The MCP server communicates with the Context Marketplace web application through its REST API:

- `GET /api/contexts` - List all contexts
- `GET /api/contexts/{id}` - Get specific context
- `GET /api/user/repositories-with-contexts` - List user repositories with context status
- `POST /api/contexts` - Create new context

## Authentication

The MCP server relies on the web application's authentication system. Users must be logged in to the Context Marketplace web interface for the MCP server to access their repositories and contexts.

## Development

### Adding New Tools

To add new tools to the MCP server:

1. Add the tool definition in `list_tools()`
2. Implement the tool handler in `call_tool()`
3. Add any necessary helper methods

### Testing

Test the MCP server using the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector python -m app.main --mcp
```

## Troubleshooting

### Common Issues

1. **Authentication errors**: Ensure you're logged in to the Context Marketplace web interface
2. **Connection refused**: Verify the web application is running on the specified URL
3. **Tool not found**: Check that all required dependencies are installed

### Logs

Check the MCP server logs:
```bash
docker-compose logs mcp-server
```

## Security Considerations

- The MCP server has the same access permissions as the authenticated user
- Private repositories and contexts are only accessible to their owners
- All GitHub API calls use the user's authenticated token

## Contributing

To contribute to the MCP server:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.