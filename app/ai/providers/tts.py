import logging
from typing import Any, Dict, Optional

from ...core.config import settings
from .base import ProviderError, TextToSpeechError, TextToSpeechProvider

logger = logging.getLogger(__name__)


class FakeTextToSpeechProvider(TextToSpeechProvider):
    def synthesize(self, text: str, voice: Optional[str] = None) -> Dict[str, Any]:
        cleaned = (text or "").strip()
        if not cleaned:
            raise TextToSpeechError("Text to speak is empty", code="empty")
        return {
            "audio": b"FAKE_TTS_AUDIO:" + cleaned.encode("utf-8")[:200],
            "content_type": "audio/mpeg",
            "provider": "fake",
            "voice": voice or settings.TTS_VOICE,
        }


class OpenAITextToSpeechProvider(TextToSpeechProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        voice: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or settings.TTS_API_KEY or settings.OPENAI_API_KEY or settings.EMBEDDING_API_KEY
        self.model = model or settings.TTS_MODEL
        self.voice = voice or settings.TTS_VOICE
        self.timeout = timeout or settings.TTS_TIMEOUT
        if not self.api_key:
            raise TextToSpeechError("TTS_API_KEY or OPENAI_API_KEY is not configured", code="config")

    def synthesize(self, text: str, voice: Optional[str] = None) -> Dict[str, Any]:
        cleaned = (text or "").strip()
        if not cleaned:
            raise TextToSpeechError("Text to speak is empty", code="empty")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise TextToSpeechError("Text-to-speech provider is not installed", code="config") from exc

        chosen_voice = voice or self.voice
        client = OpenAI(api_key=self.api_key, timeout=self.timeout)
        try:
            response = client.audio.speech.create(
                model=self.model,
                voice=chosen_voice,
                input=cleaned[:4096],
            )
            audio = response.read() if hasattr(response, "read") else bytes(response)
        except Exception as exc:
            logger.warning("Text-to-speech provider failed: %s", exc.__class__.__name__)
            message = str(exc).lower()
            if "voice" in message and ("invalid" in message or "unsupported" in message):
                raise TextToSpeechError("Unsupported voice configuration", code="invalid") from exc
            code = "timeout" if "timeout" in message else "provider"
            raise TextToSpeechError("Text-to-speech is temporarily unavailable", code=code) from exc

        if not audio:
            raise TextToSpeechError("Text-to-speech returned no audio", code="provider")
        return {
            "audio": audio,
            "content_type": "audio/mpeg",
            "provider": "openai",
            "voice": chosen_voice,
        }


def get_text_to_speech_provider() -> TextToSpeechProvider:
    provider = (settings.TTS_PROVIDER or "openai").lower()
    if provider == "fake":
        return FakeTextToSpeechProvider()
    if provider == "openai":
        return OpenAITextToSpeechProvider()
    raise ProviderError("text_to_speech", f"Unsupported text-to-speech provider: {settings.TTS_PROVIDER}")
