from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Environment
    environment: str = "development"
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/travel_advisor"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # JWT
    jwt_secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "RS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    
    # OpenAI
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_api_base: Optional[str] = os.getenv("OPENAI_API_BASE")
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:8501"]
    
    # Rate limiting
    rate_limit_crud_per_minute: int = 60
    rate_limit_agent_per_minute: int = 5
    
    # Security
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 5
    
    # Embedding model
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    class Config:
        env_file = ".env"


settings = Settings()

