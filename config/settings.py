"""Configuration settings for EUNA MVP."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # GROQ Configuration
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    
    # Pinecone Configuration
    pinecone_api_key: Optional[str] = Field(default=None, env="PINECONE_API_KEY")
    pinecone_environment: Optional[str] = Field(default=None, env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="euna-memory", env="PINECONE_INDEX_NAME")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///euna_mvp.db", env="DATABASE_URL")
    
    # Application Configuration
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL").
    max_agents: int = Field(default=10, env="MAX_AGENTS")
    task_timeout: int = Field(default=300, env="TASK_TIMEOUT")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    frontend_port: int = Field(default=8501, env="FRONTEND_PORT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
