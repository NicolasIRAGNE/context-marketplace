The project is a web application that allows users to create and manage their own projects' context.
A context is a collection of files that are used to describe a project.
The user should be able to load a repository from Github and browse / create contexts.
Context, as a whole, is a collection of files that are used to describe a project.
Individual files can be added, removed, and edited.

When creating a context, some files are created by default:

```
.context/
    stack.md # describes the stack of the project (languages, frameworks, tools, etc.)
    business.md # describes the business logic of the project
    people.md # who are the people involved in the project
    guidelines.md
```

Some of these files can be pre-filled with the help of AI or API calls.
- stack.md: basic info can be retrieved (eg languages) + repo can be analyzed by LLM
- business.md: can be retrieved from the repo description
- people.md: a list of repo contributors should be displayed to the user with checkboxes to select which ones should be included in the context. Their github profile should be displayed.
- guidelines.md: can be retrieved from eg a .github/CONTRIBUTING.md file

The user should be able to edit or regenerate any of these files, as well as add arbitrary files.

A short description of how this works that is destined to be appended to the CLAUDE.md file is provided.

