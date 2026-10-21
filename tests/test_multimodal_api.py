from io import BytesIO
from uuid import uuid4

from app.ai.providers.base import SpeechToTextError, TextToSpeechError, VisionError
from app.controllers import multimodal as multimodal_controller
from app.controllers import planning as planning_controller
from app.schemas.planning import PlanningRequest
from app.services.multimodal import MultimodalService

MIN_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


class FakePlanningService:
    def __init__(self, db=None):
        self.db = db
        self.requests = []

    def plan_trip(self, user_id, request: PlanningRequest):
        self.requests.append(request)
        return {
            "trip_id": request.trip_id,
            "destination": request.destination or "Paris",
            "summary": "A 3-day plan for Paris",
            "itinerary": [{"day": 1, "activities": ["Louvre"]}],
            "tools_used": ["mcp_get_weather"],
            "warnings": [],
            "message": "Trip plan generated successfully",
        }


class RecordingSTT:
    def transcribe(self, audio, filename, content_type=None):
        return {"text": "Plan my Paris trip and include weather-friendly activities.", "provider": "fake"}


class RecordingVision:
    def analyze(self, image, prompt, content_type=None, filename=None):
        return {"text": "Image shows the Eiffel Tower in Paris.", "provider": "fake"}


class RecordingTTS:
    def synthesize(self, text, voice=None):
        return {"audio": b"AUDIO", "content_type": "audio/mpeg", "provider": "fake", "voice": voice or "alloy"}


def test_speech_to_text_api_success(auth_client, monkeypatch):
    class Service:
        def __init__(self, db=None):
            self.db = db

        def transcribe(self, audio, filename, content_type=None):
            return {"text": "Plan my Paris trip", "provider": "fake"}

    monkeypatch.setattr(multimodal_controller, "MultimodalService", Service)
    response = auth_client.post(
        "/multimodal/speech-to-text",
        files={"audio": ("request.wav", BytesIO(b"RIFF....WAVE"), "audio/wav")},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Plan my Paris trip"


def test_speech_to_text_api_invalid(auth_client, monkeypatch):
    class Service:
        def __init__(self, db=None):
            self.db = db

        def transcribe(self, audio, filename, content_type=None):
            raise SpeechToTextError("Audio file is empty", code="empty")

    monkeypatch.setattr(multimodal_controller, "MultimodalService", Service)
    response = auth_client.post(
        "/multimodal/speech-to-text",
        files={"audio": ("request.wav", BytesIO(b""), "audio/wav")},
    )
    assert response.status_code == 400


def test_text_to_speech_api_success(auth_client, monkeypatch):
    class Service:
        def __init__(self, db=None):
            self.db = db

        def speak(self, text, voice=None):
            return {"audio": b"AUDIO", "content_type": "audio/mpeg", "provider": "fake"}

    monkeypatch.setattr(multimodal_controller, "MultimodalService", Service)
    response = auth_client.post("/multimodal/text-to-speech", data={"text": "A Paris plan."})
    assert response.status_code == 200
    assert response.content == b"AUDIO"


def test_text_to_speech_api_empty(auth_client, monkeypatch):
    class Service:
        def __init__(self, db=None):
            self.db = db

        def speak(self, text, voice=None):
            raise TextToSpeechError("Text to speak is empty", code="empty")

    monkeypatch.setattr(multimodal_controller, "MultimodalService", Service)
    response = auth_client.post("/multimodal/text-to-speech", data={"text": "x", "response_format": "json"})
    assert response.status_code == 400


def test_vision_api_failure(auth_client, monkeypatch):
    class Service:
        def __init__(self, db=None):
            self.db = db

        def analyze_image(self, image, filename, content_type, prompt=None):
            raise VisionError("Image understanding is temporarily unavailable", code="provider")

    monkeypatch.setattr(multimodal_controller, "MultimodalService", Service)
    response = auth_client.post(
        "/multimodal/vision",
        files={"image": ("paris.jpg", BytesIO(MIN_JPEG), "image/jpeg")},
    )
    assert response.status_code == 503


def test_planning_voice_reuses_existing_planner(auth_client, db_session, monkeypatch):
    planner = FakePlanningService()

    def factory(db, planning_service=None, **kwargs):
        return MultimodalService(db, planning_service=planner, stt=RecordingSTT(), tts=RecordingTTS())

    monkeypatch.setattr(planning_controller, "MultimodalService", factory)
    response = auth_client.post(
        "/planning/voice",
        data={"destination": "Paris", "days": "3", "include_speech": "true"},
        files={"audio": ("request.wav", BytesIO(b"RIFF....WAVE"), "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transcription"].startswith("Plan my Paris")
    assert body["itinerary"][0]["activities"] == ["Louvre"]
    assert body["audio_base64"]
    assert planner.requests[0].message.startswith("Plan my Paris")


def test_planning_image_reuses_existing_planner(auth_client, monkeypatch):
    planner = FakePlanningService()

    def factory(db, planning_service=None, **kwargs):
        return MultimodalService(db, planning_service=planner, vision=RecordingVision())

    monkeypatch.setattr(planning_controller, "MultimodalService", factory)
    response = auth_client.post(
        "/planning/image",
        data={"message": "Plan a museum-heavy trip", "destination": "Paris"},
        files={"image": ("paris.jpg", BytesIO(MIN_JPEG), "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "Eiffel Tower" in body["vision_context"]
    assert "Image context" in planner.requests[0].message
    assert "museum-heavy" in planner.requests[0].message


def test_generate_ai_voice_uses_planner(auth_client, monkeypatch):
    from app.controllers import itinerary as itinerary_controller

    planner = FakePlanningService()

    def factory(db, planning_service=None, **kwargs):
        return MultimodalService(db, planning_service=planner, stt=RecordingSTT())

    monkeypatch.setattr(itinerary_controller, "MultimodalService", factory)
    trip_id = uuid4()
    response = auth_client.post(
        f"/itineraries/{trip_id}/generate-ai/voice",
        files={"audio": ("request.wav", BytesIO(b"RIFF....WAVE"), "audio/wav")},
    )
    assert response.status_code == 201
    assert planner.requests[0].trip_id == trip_id
    assert planner.requests[0].persist_itinerary is True


def test_mcp_tools_api(auth_client):
    response = auth_client.get("/mcp/tools")
    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["tools"]}
    assert "mcp_get_weather" in names


def test_mcp_tool_invalid_arguments(auth_client):
    response = auth_client.post("/mcp/tools/mcp_get_weather", json={"arguments": {}})
    assert response.status_code == 400


def test_multimodal_requires_auth(client):
    response = client.post(
        "/multimodal/speech-to-text",
        files={"audio": ("request.wav", BytesIO(b"RIFF....WAVE"), "audio/wav")},
    )
    assert response.status_code in {401, 403}
