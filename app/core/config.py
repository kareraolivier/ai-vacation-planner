from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # App
    ENVIRONMENT: str = "development"
    DATABASE_POOL_SIZE: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()