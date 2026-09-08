from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
load_dotenv()


class Settings(BaseSettings):

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ENVIRONMENT: str = "development"
    DATABASE_POOL_SIZE: int = 10

    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL: str = "claude-haiku-4-5"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    LLM_MAX_RETRIES: int = 2

    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_DIMENSIONS: int = 1536

    VECTOR_STORE_PROVIDER: str = "qdrant"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "travel_knowledge"
    QDRANT_TIMEOUT: float = 10.0

    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 120
    RAG_TOP_K: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
