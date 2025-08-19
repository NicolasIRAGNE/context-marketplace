# Context Marketplace

A web application that allows users to create and manage LLM-ready code contexts from GitHub repositories, with Model Context Protocol (MCP) server integration.

## Features

- **Repository Integration**: Browse and import from GitHub repositories (personal + organizations)
- **Context Generation**: Automatically generate structured contexts (stack.md, business.md, people.md, guidelines.md)
- **Real-time Updates**: Live editing of context files and contributor selection
- **MCP Server**: Programmatic access for AI assistants like Claude
- **GitHub OAuth**: Secure authentication with repository access
- **Modern UI**: Clean, responsive design with fuzzy search capabilities

## Setup

### 1. GitHub OAuth App

1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Click "New OAuth App"
3. Fill in:
   - Application name: Context Marketplace
   - Homepage URL: http://localhost:8000
   - Authorization callback URL: http://localhost:8000/callback
4. Save your Client ID and Client Secret

### 2. Environment Configuration

Copy `.env.example` to `.env` and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
SECRET_KEY=your-secret-key-here
```

### 3. Running the Application

#### Option A: Using Python directly

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r mcp_requirements.txt

# Run the web application
python -m app.main

# Run the MCP server
python -m app.main --mcp
```

#### Option B: Using Docker (Recommended)

```bash
# Build and run with Docker Compose (includes MCP server)
docker-compose up --build
```

The application will be available at:
- **Web Interface**: http://localhost:8000
- **MCP Server**: Available via stdio for AI assistant integration

## Project Structure

```
context-marketplace/
├── app/
│   ├── config.py      # Configuration settings
│   ├── main.py        # FastAPI application + MCP server
│   ├── mcp_server.py  # MCP protocol handlers
│   ├── models.py      # Pydantic models
│   └── services.py    # Business logic
├── templates/         # Jinja2 templates
│   ├── base.html      # Base template
│   ├── index.html     # Home page
│   ├── profile.html   # User profile
│   ├── repositories.html  # Repository browser
│   └── context_detail.html # Context viewer/editor
├── static/            # Static files
├── contexts/          # Generated context storage
├── requirements.txt   # Python dependencies
├── mcp_requirements.txt # MCP server dependencies
├── Dockerfile         # Single container for both modes
├── docker-compose.yml # Multi-service setup
└── MCP_README.md      # MCP integration guide
```

## MCP Integration

The Context Marketplace includes a Model Context Protocol (MCP) server that allows AI assistants like Claude to programmatically access contexts. See [MCP_README.md](MCP_README.md) for detailed setup and usage instructions.

### Quick MCP Setup for Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "context-marketplace": {
      "command": "docker",
      "args": [
        "exec", "-i", "context-marketplace-mcp-server-1", 
        "python", "start_mcp_server.py"
      ]
    }
  }
}
```

## Development

The application runs in debug mode by default with auto-reload enabled.

### Available MCP Tools
- **search_contexts** - Find contexts by name/description
- **get_context_details** - Get full context information
- **list_contexts** - List all available contexts
- **get_context_files** - Get all files from a specific context

### Running MCP Mode
```bash
# Web server mode (default)
python -m app.main

# MCP server mode
python -m app.main --mcp
```

## Technologies

- **FastAPI** - Web framework
- **Jinja2** - Template engine  
- **Tailwind CSS** - Styling
- **Authlib** - OAuth integration
- **Docker** - Containerization
- **MCP** - Model Context Protocol for AI integration
- **Pydantic** - Data validation and serialization