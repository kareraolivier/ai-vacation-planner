import io
import logging
from typing import Any, Dict, Optional

from ...core.config import settings
from .base import ProviderError, SpeechToTextError, SpeechToTextProvider
from .media import validate_audio

logger = logging.getLogger(__name__)


class FakeSpeechToTextProvider(SpeechToTextProvider):
    def transcribe(self, audio: bytes, filename: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        validate_audio(
            audio,
            filename,
            content_type,
            settings.STT_MAX_BYTES,
            settings.STT_ALLOWED_FORMATS,
        )
        return {
            "text": "Plan my Paris trip and include weather-friendly activities.",
            "provider": "fake",
        }


class OpenAISpeechToTextProvider(SpeechToTextProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or settings.STT_API_KEY or settings.OPENAI_API_KEY or settings.EMBEDDING_API_KEY
        self.model = model or settings.STT_MODEL
        self.timeout = timeout or settings.STT_TIMEOUT
        if not self.api_key:
            raise SpeechToTextError("STT_API_KEY or OPENAI_API_KEY is not configured", code="config")

    def transcribe(self, audio: bytes, filename: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        validate_audio(
            audio,
            filename,
            content_type,
            settings.STT_MAX_BYTES,
            settings.STT_ALLOWED_FORMATS,
        )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise SpeechToTextError("Speech-to-text provider is not installed", code="config") from exc

        client = OpenAI(api_key=self.api_key, timeout=self.timeout)
        buffer = io.BytesIO(audio)
        buffer.name = filename or "audio.wav"
        try:
            result = client.audio.transcriptions.create(model=self.model, file=buffer)
        except Exception as exc:
            logger.warning("Speech-to-text provider failed: %s", exc.__class__.__name__)
            message = str(exc).lower()
            code = "timeout" if "timeout" in message else "provider"
            raise SpeechToTextError("Speech-to-text is temporarily unavailable", code=code) from exc

        text = (getattr(result, "text", None) or "").strip()
        if not text:
            raise SpeechToTextError("Could not transcribe the audio", code="provider")
        return {"text": text, "provider": "openai"}


def get_speech_to_text_provider() -> SpeechToTextProvider:
    provider = (settings.STT_PROVIDER or "openai").lower()
    if provider == "fake":
        return FakeSpeechToTextProvider()
    if provider == "openai":
        return OpenAISpeechToTextProvider()
    raise ProviderError("speech_to_text", f"Unsupported speech-to-text provider: {settings.STT_PROVIDER}")
