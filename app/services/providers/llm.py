from typing import Optional

from ...core.config import settings


class LLMConfigurationError(Exception):
    pass


def get_chat_model(temperature: Optional[float] = None):
    provider = (settings.LLM_PROVIDER or "openai").lower()
    if provider != "openai":
        raise LLMConfigurationError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
    if not settings.LLM_API_KEY:
        raise LLMConfigurationError("LLM_API_KEY is not configured")

    from langchain_openai import ChatOpenAI

    kwargs = {
        "model": settings.LLM_MODEL,
        "api_key": settings.LLM_API_KEY,
        "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature,
        "max_retries": settings.LLM_MAX_RETRIES,
    }
    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    return ChatOpenAI(**kwargs)
