from typing import Optional, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..schemas.multimodal import (
    MultimodalErrorResponse,
    SpeechJsonResponse,
    TranscriptionResponse,
    VisionResponse,
)
from ..schemas.planning import PlanningErrorResponse, PlanningRequest, PlanningResponse
from ..services.multimodal import MultimodalService
from .errors import raise_capability_error

router = APIRouter(prefix="/multimodal", tags=["Multimodal"])

_ERROR_RESPONSES = {
    400: {"model": MultimodalErrorResponse, "description": "Empty or invalid input"},
    401: {"model": MultimodalErrorResponse, "description": "Missing or invalid token"},
    413: {"model": MultimodalErrorResponse, "description": "File too large"},
    415: {"model": MultimodalErrorResponse, "description": "Unsupported media type"},
    503: {"model": MultimodalErrorResponse, "description": "Provider unavailable or misconfigured"},
}


@router.post(
    "/speech-to-text",
    response_model=TranscriptionResponse,
    responses=_ERROR_RESPONSES,
    summary="Transcribe spoken trip input",
    description=(
        "Accepts an audio file and returns transcribed text. "
        "Supported formats: mp3, wav, m4a, webm, ogg, flac. "
        "The text can be sent to the existing planner."
    ),
)
def speech_to_text(
    audio: UploadFile = File(..., description="Spoken trip request"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    try:
        result = MultimodalService(db).transcribe(
            audio.file.read(),
            audio.filename or "audio.wav",
            audio.content_type,
        )
    except Exception as exc:
        raise_capability_error(exc)
    return TranscriptionResponse(text=result["text"], provider=result["provider"], message="Audio transcribed")


@router.post(
    "/text-to-speech",
    responses={
        **_ERROR_RESPONSES,
        200: {"content": {"audio/mpeg": {}}, "description": "Spoken travel plan audio"},
    },
    summary="Speak a travel plan",
    description="Converts itinerary text into speech. Returns audio/mpeg. Text is not discarded; send it in the form field.",
)
def text_to_speech(
    text: str = Form(..., min_length=1, max_length=8000, description="Travel plan or summary to speak"),
    voice: Optional[str] = Form(None, description="Optional provider voice name"),
    response_format: str = Form("audio", description="audio or json"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    try:
        result = MultimodalService(db).speak(text, voice)
    except Exception as exc:
        raise_capability_error(exc)
    if response_format == "json":
        import base64
        return SpeechJsonResponse(
            audio_base64=base64.b64encode(result["audio"]).decode("ascii"),
            content_type=result["content_type"],
            provider=result["provider"],
            message="Speech generated",
        )
    return Response(content=result["audio"], media_type=result["content_type"])


@router.post(
    "/vision",
    response_model=VisionResponse,
    responses=_ERROR_RESPONSES,
    summary="Extract travel context from an image",
    description="Supported images: jpeg, png, gif, webp. Extracted text is meant to be combined with a planning request.",
)
def understand_image(
    image: UploadFile = File(..., description="Destination, map, hotel, or itinerary image"),
    prompt: Optional[str] = Form(None, description="Optional extraction hint"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    try:
        result = MultimodalService(db).analyze_image(
            image.file.read(),
            image.filename,
            image.content_type,
            prompt,
        )
    except Exception as exc:
        raise_capability_error(exc)
    return VisionResponse(text=result["text"], provider=result["provider"], message="Image understood")


@router.post(
    "/plan/voice",
    response_model=PlanningResponse,
    responses={**_ERROR_RESPONSES, 404: {"model": PlanningErrorResponse, "description": "Trip not found"}},
    summary="Plan a trip from voice using the existing planner",
)
def plan_from_voice(
    audio: UploadFile = File(..., description="Spoken trip request"),
    trip_id: Optional[UUID] = Form(None),
    destination: Optional[str] = Form(None),
    days: Optional[int] = Form(None),
    budget: Optional[float] = Form(None),
    trip_style: Optional[str] = Form(None),
    persist_itinerary: bool = Form(True),
    include_speech: bool = Form(False, description="Also return spoken audio as base64"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id: UUID = cast(UUID, current_user.id)
    request = PlanningRequest(
        message="Plan this trip.",
        trip_id=trip_id,
        destination=destination,
        days=days,
        budget=budget,
        trip_style=trip_style,
        persist_itinerary=persist_itinerary,
    )
    try:
        return MultimodalService(db).plan_from_voice(
            user_id,
            audio.file.read(),
            audio.filename or "audio.wav",
            audio.content_type,
            request,
            include_speech=include_speech,
        )
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if str(exc) == "Trip not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc))
    except Exception as exc:
        raise_capability_error(exc)


@router.post(
    "/plan/image",
    response_model=PlanningResponse,
    responses={**_ERROR_RESPONSES, 404: {"model": PlanningErrorResponse, "description": "Trip not found"}},
    summary="Plan a trip from an image plus optional text using the existing planner",
)
def plan_from_image(
    image: UploadFile = File(..., description="Travel-related image"),
    message: Optional[str] = Form(None, description="Optional text request to combine with the image"),
    trip_id: Optional[UUID] = Form(None),
    destination: Optional[str] = Form(None),
    days: Optional[int] = Form(None),
    budget: Optional[float] = Form(None),
    trip_style: Optional[str] = Form(None),
    persist_itinerary: bool = Form(True),
    include_speech: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id: UUID = cast(UUID, current_user.id)
    request = PlanningRequest(
        message=message or "Plan this trip using the image.",
        trip_id=trip_id,
        destination=destination,
        days=days,
        budget=budget,
        trip_style=trip_style,
        persist_itinerary=persist_itinerary,
    )
    try:
        return MultimodalService(db).plan_from_image(
            user_id,
            image.file.read(),
            image.filename,
            image.content_type,
            request,
            include_speech=include_speech,
        )
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if str(exc) == "Trip not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc))
    except Exception as exc:
        raise_capability_error(exc)
