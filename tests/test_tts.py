import pytest

from app.ai.providers.base import TextToSpeechError
from app.ai.providers.tts import FakeTextToSpeechProvider


class BrokenTTS:
    def synthesize(self, text, voice=None):
        raise TextToSpeechError("Text-to-speech is temporarily unavailable", code="provider")


def test_text_to_speech_success():
    result = FakeTextToSpeechProvider().synthesize("A 3-day Paris plan.")
    assert result["audio"].startswith(b"FAKE_TTS_AUDIO:")
    assert result["content_type"] == "audio/mpeg"


def test_text_to_speech_empty_text():
    with pytest.raises(TextToSpeechError) as exc:
        FakeTextToSpeechProvider().synthesize("   ")
    assert exc.value.code == "empty"


def test_text_to_speech_provider_failure():
    with pytest.raises(TextToSpeechError) as exc:
        BrokenTTS().synthesize("Hello")
    assert exc.value.code == "provider"
