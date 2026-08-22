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

    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_TEMPERATURE: float = 0.3
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
    AGENT_MAX_TOOL_ITERATIONS: int = 6

    WEATHER_PROVIDER: str = "openmeteo"
    WEATHER_API_URL: str = "https://api.open-meteo.com/v1"
    WEATHER_GEOCODE_URL: str = "https://geocoding-api.open-meteo.com/v1"
    WEATHER_API_KEY: Optional[str] = None
    WEATHER_TIMEOUT: float = 10.0

    MAPS_PROVIDER: str = "nominatim"
    MAPS_API_URL: str = "https://nominatim.openstreetmap.org"
    MAPS_API_KEY: Optional[str] = None
    MAPS_USER_AGENT: str = "ai-vacation-planner/1.0"
    MAPS_TIMEOUT: float = 10.0

    PRICING_PROVIDER: str = "http"
    PRICING_API_URL: Optional[str] = None
    PRICING_API_KEY: Optional[str] = None
    PRICING_TIMEOUT: float = 10.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore" 

settings = Settings()
