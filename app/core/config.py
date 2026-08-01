from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv
load_dotenv()


class Settings(BaseSettings):

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ENVIRONMENT: str = "development"
    DATABASE_POOL_SIZE: int = 10

    # LLM API Keys
    ANTHROPIC_API_KEY: Optional[str] = None

    # Weather API Key
    OPENWEATHER_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
