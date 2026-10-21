import base64
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..ai.providers.base import SpeechToTextProvider, TextToSpeechProvider, VisionProvider
from ..ai.providers.speech import get_speech_to_text_provider
from ..ai.providers.tts import get_text_to_speech_provider
from ..ai.providers.vision import DEFAULT_VISION_PROMPT, get_vision_provider
from ..schemas.planning import PlanningRequest
from .planning import PlanningService


def itinerary_to_speech_text(
    destination: Optional[str],
    summary: Optional[str],
    itinerary: Optional[List[Dict[str, Any]]] = None,
) -> str:
    lines = []
    if summary:
        lines.append(summary)
    elif destination:
        lines.append(f"Here is your trip plan for {destination}.")
    else:
        lines.append("Here is your trip plan.")
    for item in itinerary or []:
        day = item.get("day")
        activities = ", ".join(item.get("activities") or [])
        if activities:
            lines.append(f"Day {day}: {activities}.")
    return " ".join(lines).strip()


class MultimodalService:
    def __init__(
        self,
        db: Session,
        planning_service: Optional[PlanningService] = None,
        stt: Optional[SpeechToTextProvider] = None,
        tts: Optional[TextToSpeechProvider] = None,
        vision: Optional[VisionProvider] = None,
    ):
        self.db = db
        self.planning_service = planning_service or PlanningService(db)
        self._stt = stt
        self._tts = tts
        self._vision = vision

    @property
    def stt(self) -> SpeechToTextProvider:
        if self._stt is None:
            self._stt = get_speech_to_text_provider()
        return self._stt

    @property
    def tts(self) -> TextToSpeechProvider:
        if self._tts is None:
            self._tts = get_text_to_speech_provider()
        return self._tts

    @property
    def vision(self) -> VisionProvider:
        if self._vision is None:
            self._vision = get_vision_provider()
        return self._vision

    def transcribe(self, audio: bytes, filename: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        return self.stt.transcribe(audio, filename, content_type)

    def speak(self, text: str, voice: Optional[str] = None) -> Dict[str, Any]:
        return self.tts.synthesize(text, voice)

    def analyze_image(
        self,
        image: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.vision.analyze(
            image,
            prompt or DEFAULT_VISION_PROMPT,
            content_type=content_type,
            filename=filename,
        )

    def plan_from_voice(
        self,
        user_id: UUID,
        audio: bytes,
        filename: str,
        content_type: Optional[str],
        request: PlanningRequest,
        include_speech: bool = False,
    ) -> dict:
        transcribed = self.transcribe(audio, filename, content_type)
        planning_request = request.model_copy(update={"message": transcribed["text"]})
        result = self.planning_service.plan_trip(user_id, planning_request)
        result["transcription"] = transcribed["text"]
        if include_speech:
            self._attach_speech(result)
        return result

    def plan_from_image(
        self,
        user_id: UUID,
        image: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        request: PlanningRequest,
        include_speech: bool = False,
    ) -> dict:
        extracted = self.analyze_image(image, filename, content_type)
        combined = request.message.strip()
        if extracted.get("text"):
            combined = (
                f"{combined}\n\nImage context:\n{extracted['text']}"
                if combined
                else extracted["text"]
            )
        planning_request = request.model_copy(update={"message": combined or "Plan this trip."})
        result = self.planning_service.plan_trip(user_id, planning_request)
        result["vision_context"] = extracted.get("text")
        if include_speech:
            self._attach_speech(result)
        return result

    def speak_plan(
        self,
        destination: Optional[str] = None,
        summary: Optional[str] = None,
        itinerary: Optional[List[Dict[str, Any]]] = None,
        text: Optional[str] = None,
        voice: Optional[str] = None,
    ) -> Dict[str, Any]:
        spoken = (text or "").strip() or itinerary_to_speech_text(destination, summary, itinerary)
        return self.speak(spoken, voice)

    def _attach_speech(self, result: dict) -> None:
        try:
            speech = self.speak_plan(
                destination=result.get("destination"),
                summary=result.get("summary"),
                itinerary=result.get("itinerary"),
            )
            result["audio_base64"] = base64.b64encode(speech["audio"]).decode("ascii")
            result["audio_content_type"] = speech.get("content_type") or "audio/mpeg"
        except Exception:
            warnings = list(result.get("warnings") or [])
            warnings.append("Spoken response is temporarily unavailable")
            result["warnings"] = warnings
