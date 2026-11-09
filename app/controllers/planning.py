from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from typing import Optional, cast
from uuid import UUID

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..schemas.planning import PlanningErrorResponse, PlanningRequest, PlanningResponse
from ..services.multimodal import MultimodalService
from ..services.planning import PlanningService
from ..ai.providers.base import MultimodalError
from ..ai.rag.embeddings import EmbeddingError
from ..ai.rag.vector_store import VectorStoreError
from .errors import raise_capability_error

router = APIRouter(prefix="/planning", tags=["AI Planning"])


@router.post(
    "/",
    response_model=PlanningResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": PlanningErrorResponse, "description": "Invalid request or trip not found"},
        401: {"model": PlanningErrorResponse, "description": "Missing or invalid token"},
        404: {"model": PlanningErrorResponse, "description": "Trip not found"},
        503: {"model": PlanningErrorResponse, "description": "LLM, tool, or knowledge backend unavailable"},
    },
    summary="Generate a vacation plan with the tool-using agent",
    description=(
        "Runs the LangGraph planning agent. The model selects tools (weather, maps, pricing, "
        "travel knowledge) only when they are useful, then composes a day-by-day itinerary. "
        "When trip_id is provided and persist_itinerary is true, the itinerary is stored with "
        "the existing itinerary service."
    ),
)
def plan_vacation(
    request: PlanningRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PlanningService(db)
    user_id: UUID = cast(UUID, current_user.id)
    try:
        return service.plan_trip(user_id, request)
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if str(exc) == "Trip not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc))
    except (RuntimeError, EmbeddingError, VectorStoreError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post(
    "/voice",
    response_model=PlanningResponse,
    responses={
        400: {"model": PlanningErrorResponse, "description": "Empty or invalid audio"},
        401: {"model": PlanningErrorResponse, "description": "Missing or invalid token"},
        404: {"model": PlanningErrorResponse, "description": "Trip not found"},
        413: {"model": PlanningErrorResponse, "description": "Audio too large"},
        415: {"model": PlanningErrorResponse, "description": "Unsupported audio format"},
        503: {"model": PlanningErrorResponse, "description": "Speech or planner unavailable"},
    },
    summary="Plan a trip from voice",
    description=(
        "Transcribes the uploaded audio, then runs the existing PlanningService / LangGraph agent. "
        "Supported audio: mp3, wav, m4a, webm, ogg, flac. Returns the transcription with the plan. "
        "Set include_speech=true to also receive spoken audio as base64."
    ),
)
def plan_vacation_from_voice(
    audio: UploadFile = File(..., description="Spoken trip request"),
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
    except (RuntimeError, EmbeddingError, VectorStoreError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except MultimodalError as exc:
        raise_capability_error(exc)


@router.post(
    "/image",
    response_model=PlanningResponse,
    responses={
        400: {"model": PlanningErrorResponse, "description": "Empty or invalid image"},
        401: {"model": PlanningErrorResponse, "description": "Missing or invalid token"},
        404: {"model": PlanningErrorResponse, "description": "Trip not found"},
        413: {"model": PlanningErrorResponse, "description": "Image too large"},
        415: {"model": PlanningErrorResponse, "description": "Unsupported image format"},
        503: {"model": PlanningErrorResponse, "description": "Vision or planner unavailable"},
    },
    summary="Plan a trip from an image plus optional text",
    description=(
        "Sends the image to a vision model, combines the extracted context with the optional message, "
        "then runs the existing PlanningService. Supported images: jpeg, png, gif, webp."
    ),
)
def plan_vacation_from_image(
    image: UploadFile = File(..., description="Destination, map, hotel, or itinerary image"),
    message: Optional[str] = Form(None, description="Optional text request"),
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
    except (RuntimeError, EmbeddingError, VectorStoreError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except MultimodalError as exc:
        raise_capability_error(exc)
