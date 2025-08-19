# Technology Stack

## Languages
- **Python**: 100% (backend implementation)
- **HTML**: Templates and frontend structure  
- **JavaScript**: Client-side interactivity
- **CSS**: Styling via Tailwind CSS

## Backend Framework
- **FastAPI** - Modern, fast web API framework
- **Uvicorn[standard]** - ASGI server for running FastAPI
- **Python-multipart** - Form data handling

## Authentication & Security
- **Authlib** - OAuth integration (GitHub OAuth)
- **Itsdangerous** - Secure session handling

## Data & Validation
- **Pydantic** - Data validation and serialization
- **Pydantic-settings** - Configuration management
- **Python-dotenv** - Environment variable management

## HTTP Client
- **HTTPX** - Async HTTP client for GitHub API calls

## Frontend & Templates
- **Jinja2** - Server-side HTML templating
- **Tailwind CSS** - Utility-first CSS framework (via CDN)
- **Vanilla JavaScript** - Client-side functionality

## Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Local development environment

## Storage
- **File-based storage** - Context data stored as JSON files
- **Local filesystem** - Context files stored in organized directories

## Architecture
- **MVC Pattern** - Models, Views (templates), Controllers (FastAPI routes)
- **Service Layer** - Business logic separated in services.py
- **RESTful API** - Standard REST endpoints for CRUD operations