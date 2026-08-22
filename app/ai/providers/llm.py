from typing import Optional

from ...core.config import settings


class LLMConfigurationError(Exception):
    pass


def get_chat_model(temperature: Optional[float] = None):
    """LangChain Claude client for tool-calling. Compose still uses app.ai.llm.LLMService."""
    if not settings.ANTHROPIC_API_KEY:
        raise LLMConfigurationError("ANTHROPIC_API_KEY is not configured")

    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.LLM_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
        max_retries=settings.LLM_MAX_RETRIES,
    )
