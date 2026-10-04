import pytest

from app.ai.providers.base import SpeechToTextError
from app.ai.providers.speech import FakeSpeechToTextProvider


class BrokenSTT:
    def transcribe(self, audio, filename, content_type=None):
        raise SpeechToTextError("Speech-to-text is temporarily unavailable", code="provider")


def test_speech_to_text_success():
    result = FakeSpeechToTextProvider().transcribe(b"RIFF....WAVE", "request.wav", "audio/wav")
    assert "Paris" in result["text"]
    assert result["provider"] == "fake"


def test_speech_to_text_empty_audio():
    with pytest.raises(SpeechToTextError) as exc:
        FakeSpeechToTextProvider().transcribe(b"", "request.wav", "audio/wav")
    assert exc.value.code == "empty"


def test_speech_to_text_too_large(monkeypatch):
    from app.ai.providers import speech as speech_module

    monkeypatch.setattr(speech_module.settings, "STT_MAX_BYTES", 4)
    with pytest.raises(SpeechToTextError) as exc:
        FakeSpeechToTextProvider().transcribe(b"RIFF....WAVE", "request.wav", "audio/wav")
    assert exc.value.code == "too_large"


def test_speech_to_text_unsupported_format():
    with pytest.raises(SpeechToTextError) as exc:
        FakeSpeechToTextProvider().transcribe(b"not-audio", "notes.txt", "text/plain")
    assert exc.value.code == "unsupported"


def test_speech_to_text_provider_failure():
    with pytest.raises(SpeechToTextError) as exc:
        BrokenSTT().transcribe(b"RIFF....WAVE", "request.wav", "audio/wav")
    assert exc.value.code == "provider"
