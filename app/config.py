from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # GitHub OAuth
    github_client_id: str
    github_client_secret: str
    
    # Application
    secret_key: str
    app_url: str = "http://localhost:8000"
    debug: bool = True
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()