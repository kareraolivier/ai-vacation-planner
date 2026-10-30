import pytest

from app.ai.providers.base import VisionError
from app.ai.providers.vision import FakeVisionProvider

MIN_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


class BrokenVision:
    def analyze(self, image, prompt, content_type=None, filename=None):
        raise VisionError("Image understanding is temporarily unavailable", code="provider")


def test_vision_success():
    result = FakeVisionProvider().analyze(MIN_JPEG, "Extract travel details", content_type="image/jpeg", filename="paris.jpg")
    assert "Paris" in result["text"]
    assert result["provider"] == "fake"


def test_vision_empty_image():
    with pytest.raises(VisionError) as exc:
        FakeVisionProvider().analyze(b"", "Extract", filename="paris.jpg")
    assert exc.value.code == "empty"


def test_vision_invalid_image():
    with pytest.raises(VisionError) as exc:
        FakeVisionProvider().analyze(b"not-an-image", "Extract", filename="notes.txt", content_type="text/plain")
    assert exc.value.code in {"invalid", "unsupported"}


def test_vision_too_large(monkeypatch):
    from app.ai.providers import vision as vision_module

    monkeypatch.setattr(vision_module.settings, "VISION_MAX_BYTES", 8)
    with pytest.raises(VisionError) as exc:
        FakeVisionProvider().analyze(MIN_JPEG, "Extract", filename="paris.jpg", content_type="image/jpeg")
    assert exc.value.code == "too_large"


def test_vision_unsupported_format():
    with pytest.raises(VisionError) as exc:
        FakeVisionProvider().analyze(b"%PDF-1.4", "Extract", filename="file.pdf", content_type="application/pdf")
    assert exc.value.code in {"invalid", "unsupported"}


def test_vision_provider_failure():
    with pytest.raises(VisionError) as exc:
        BrokenVision().analyze(MIN_JPEG, "Extract")
    assert exc.value.code == "provider"
