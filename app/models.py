from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ContextFileType(str, Enum):
    STACK = "stack"
    BUSINESS = "business"
    PEOPLE = "people"
    GUIDELINES = "guidelines"
    CUSTOM = "custom"


class ContextFile(BaseModel):
    name: str
    file_type: ContextFileType
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class GitHubRepo(BaseModel):
    owner: str
    name: str
    full_name: str
    description: Optional[str] = None
    url: str
    clone_url: str
    default_branch: str = "main"
    language: Optional[str] = None
    languages: Optional[Dict[str, int]] = None


class GitHubContributor(BaseModel):
    login: str
    id: int
    avatar_url: str
    name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    pronouns: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    twitter_username: Optional[str] = None
    public_repos: Optional[int] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    created_at: Optional[str] = None
    hireable: Optional[bool] = None
    contributions: int
    selected: bool = False


class Context(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    owner_id: int
    owner_login: str
    github_repo: Optional[GitHubRepo] = None
    files: List[ContextFile] = Field(default_factory=list)
    contributors: List[GitHubContributor] = Field(default_factory=list)
    is_public: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CreateContextRequest(BaseModel):
    name: str
    description: Optional[str] = None
    github_repo_url: Optional[str] = None
    is_public: bool = True


class UpdateContextRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class UpdateContextFileRequest(BaseModel):
    content: str


class CreateContextFileRequest(BaseModel):
    name: str
    file_type: ContextFileType
    content: str


class GenerateFileRequest(BaseModel):
    file_type: ContextFileType
    use_ai: bool = True