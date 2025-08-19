# Business Logic

## Project Overview

Context Marketplace is a web application that helps developers create, manage, and share LLM-ready code contexts. It solves the problem of preparing codebases for Large Language Model consumption by automatically analyzing repositories and generating structured context files.

## Core Value Proposition

- **Automated Context Generation**: Transforms any GitHub repository into LLM-ready context files
- **Structured Documentation**: Creates standardized context files (stack.md, business.md, people.md, guidelines.md)
- **Community Sharing**: Enables sharing and discovery of optimized code contexts
- **GitHub Integration**: Seamless integration with GitHub repositories and contributors

## Key Features

### 1. Repository Analysis
- Connect GitHub repositories via OAuth
- Automatic language detection and analysis
- Repository metadata extraction (description, contributors, structure)

### 2. Context File Generation
- **stack.md**: Technology stack analysis with language percentages
- **business.md**: Project description and business logic documentation
- **people.md**: Contributor information with selection capability
- **guidelines.md**: Development guidelines and best practices

### 3. Context Management
- Create new contexts from GitHub repositories
- Edit and customize generated context files
- Add arbitrary custom files to contexts
- Public/private context visibility controls

### 4. User Experience
- GitHub OAuth authentication
- Intuitive web interface
- Real-time file editing
- One-click context copying for LLM use

## Business Rules

### Context Creation
1. Users must authenticate via GitHub to create contexts
2. Each context must have a unique name per user
3. Default context files are automatically generated when linking a GitHub repo
4. Users can override any auto-generated content

### Access Control
- **Public Contexts**: Visible to all users, can be viewed and copied
- **Private Contexts**: Only visible to the owner
- Only context owners can edit their contexts
- Contributors can be selected for inclusion in people.md

### File Management
- Context files are stored in organized directory structures
- Each file has a type classification (stack, business, people, guidelines, custom)
- File content is versioned with creation and update timestamps
- Files can be added, edited, or removed at any time

## User Stories

### For Individual Developers
- "I want to quickly prepare my repository for LLM analysis"
- "I need to document my project's context in a standardized format"
- "I want to share my project context with the community"

### For Teams
- "We need to onboard new team members with proper project context"
- "We want to maintain consistent documentation across projects"
- "We need to prepare multiple repositories for AI-assisted development"

### For LLM Users
- "I want ready-to-use context files for code analysis"
- "I need properly structured project information for AI prompts"
- "I want to discover well-documented open source projects"

## Success Metrics

### User Engagement
- Number of contexts created per user
- Frequency of context updates
- Public vs private context ratio

### Repository Integration
- GitHub repositories successfully connected
- Accuracy of auto-generated content
- User satisfaction with generated contexts

### Community Growth
- Number of public contexts shared
- Context discovery and usage rates
- User retention and return visits