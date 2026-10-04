import base64
import logging
from typing import Any, Dict, Optional

from ...core.config import settings
from .base import ProviderError, VisionError, VisionProvider
from .media import validate_image

logger = logging.getLogger(__name__)

DEFAULT_VISION_PROMPT = (
    "Extract travel-planning information from this image. "
    "Include destination, dates, hotels, attractions, maps, itinerary items, "
    "and any constraints that would help plan a vacation. "
    "If the image is unrelated to travel, say so briefly."
)


class FakeVisionProvider(VisionProvider):
    def analyze(
        self,
        image: bytes,
        prompt: str,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        validate_image(
            image,
            filename,
            content_type,
            settings.VISION_MAX_BYTES,
            settings.VISION_ALLOWED_FORMATS,
        )
        return {
            "text": (
                "The image shows a Paris landmark near the Seine. "
                "Useful context: destination Paris, outdoor sightseeing, museum options if weather is poor."
            ),
            "provider": "fake",
        }


class AnthropicVisionProvider(VisionProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or settings.VISION_API_KEY or settings.ANTHROPIC_API_KEY
        self.model = model or settings.VISION_MODEL or settings.LLM_MODEL
        self.timeout = timeout or settings.VISION_TIMEOUT
        if not self.api_key:
            raise VisionError("VISION_API_KEY or ANTHROPIC_API_KEY is not configured", code="config")

    def analyze(
        self,
        image: bytes,
        prompt: str,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        media_type = validate_image(
            image,
            filename,
            content_type,
            settings.VISION_MAX_BYTES,
            settings.VISION_ALLOWED_FORMATS,
        )
        try:
            import anthropic
        except ImportError as exc:
            raise VisionError("Vision provider is not installed", code="config") from exc

        client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type if media_type.startswith("image/") else "image/jpeg",
                                    "data": base64.b64encode(image).decode("ascii"),
                                },
                            },
                            {"type": "text", "text": prompt or DEFAULT_VISION_PROMPT},
                        ],
                    }
                ],
            )
            text = response.content[0].text if response.content else ""
        except Exception as exc:
            logger.warning("Vision provider failed: %s", exc.__class__.__name__)
            message = str(exc).lower()
            code = "timeout" if "timeout" in message else "provider"
            raise VisionError("Image understanding is temporarily unavailable", code=code) from exc

        cleaned = (text or "").strip()
        if not cleaned:
            raise VisionError("Could not extract information from the image", code="provider")
        return {"text": cleaned, "provider": "anthropic"}


def get_vision_provider() -> VisionProvider:
    provider = (settings.VISION_PROVIDER or "anthropic").lower()
    if provider == "fake":
        return FakeVisionProvider()
    if provider == "anthropic":
        return AnthropicVisionProvider()
    raise ProviderError("vision", f"Unsupported vision provider: {settings.VISION_PROVIDER}")
