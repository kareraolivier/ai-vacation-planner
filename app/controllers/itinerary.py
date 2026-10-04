from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.itinerary import ItineraryService
from ..services.multimodal import MultimodalService
from ..services.planning import PlanningService
from ..schemas.itinerary import GenerateAIRequest, ItineraryCreate, ItineraryOutput
from ..schemas.planning import PlanningRequest
from ..ai.providers.base import MultimodalError
from .errors import raise_capability_error
from typing import Optional, cast
from uuid import UUID

router = APIRouter(prefix="/itineraries", tags=["Itineraries"])


@router.post("/", response_model=ItineraryOutput, status_code=status.HTTP_201_CREATED)
def create_itinerary(
    itinerary_data: ItineraryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    itinerary = ItineraryService(db)
    user_id: UUID = cast(UUID, current_user.id)
    result = itinerary.create_itinerary(user_id, itinerary_data)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    return result


@router.get("/{trip_id}", response_model=ItineraryOutput)
def get_trip_itinerary(
    trip_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    itinerary = ItineraryService(db)
    user_id: UUID = cast(UUID, current_user.id)
    result = itinerary.get_trip_itinerary(user_id, trip_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    return {
        "trip_id": result["trip_id"],
        "itinerary": result["itinerary"],
        "message": "Itinerary retrieved successfully"
    }


@router.post(
    "/{trip_id}/generate-ai",
    response_model=ItineraryOutput,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Missing or invalid token"},
        404: {"description": "Trip not found"},
        503: {"description": "LLM or tool backend unavailable"},
    },
    summary="Generate an itinerary with the tool-using agent",
    description=(
        "Loads the trip, then runs the LangGraph agent. Claude chooses tools "
        "(weather, maps, pricing, travel knowledge) based on the optional message, "
        "for example: 'Plan my Paris trip and include weather-friendly activities.' "
        "Tool results are passed into the existing Claude itinerary composer and saved."
    ),
)
def generate_ai_itinerary(
    trip_id: UUID,
    request: GenerateAIRequest = GenerateAIRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id: UUID = cast(UUID, current_user.id)
    extra = request.message or "Plan this trip."
    try:
        result = PlanningService(db).plan_trip(
            user_id,
            PlanningRequest(
                message=extra,
                trip_id=trip_id,
                persist_itinerary=True,
            ),
        )
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if str(exc) == "Trip not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return {
        "trip_id": result["trip_id"],
        "itinerary": result["itinerary"],
        "message": result["message"],
    }


@router.post(
    "/{trip_id}/generate-ai/voice",
    response_model=ItineraryOutput,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Empty or invalid audio"},
        401: {"description": "Missing or invalid token"},
        404: {"description": "Trip not found"},
        413: {"description": "Audio too large"},
        415: {"description": "Unsupported audio format"},
        503: {"description": "Speech or planner unavailable"},
    },
    summary="Generate an itinerary from voice using the existing planner",
    description=(
        "Transcribes the audio, then calls the same PlanningService used by generate-ai. "
        "Supported audio: mp3, wav, m4a, webm, ogg, flac."
    ),
)
def generate_ai_itinerary_from_voice(
    trip_id: UUID,
    audio: UploadFile = File(..., description="Spoken trip request"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id: UUID = cast(UUID, current_user.id)
    request = PlanningRequest(message="Plan this trip.", trip_id=trip_id, persist_itinerary=True)
    try:
        result = MultimodalService(db).plan_from_voice(
            user_id,
            audio.file.read(),
            audio.filename or "audio.wav",
            audio.content_type,
            request,
        )
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if str(exc) == "Trip not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except MultimodalError as exc:
        raise_capability_error(exc)

    return {
        "trip_id": result["trip_id"],
        "itinerary": result["itinerary"],
        "message": result["message"],
    }


@router.post(
    "/{trip_id}/generate-ai/image",
    response_model=ItineraryOutput,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Empty or invalid image"},
        401: {"description": "Missing or invalid token"},
        404: {"description": "Trip not found"},
        413: {"description": "Image too large"},
        415: {"description": "Unsupported image format"},
        503: {"description": "Vision or planner unavailable"},
    },
    summary="Generate an itinerary from an image using the existing planner",
    description=(
        "Extracts travel context from the image, combines it with optional text, "
        "then calls the same PlanningService used by generate-ai. "
        "Supported images: jpeg, png, gif, webp."
    ),
)
def generate_ai_itinerary_from_image(
    trip_id: UUID,
    image: UploadFile = File(..., description="Travel-related image"),
    message: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id: UUID = cast(UUID, current_user.id)
    request = PlanningRequest(
        message=message or "Plan this trip using the image.",
        trip_id=trip_id,
        persist_itinerary=True,
    )
    try:
        result = MultimodalService(db).plan_from_image(
            user_id,
            image.file.read(),
            image.filename,
            image.content_type,
            request,
        )
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if str(exc) == "Trip not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except MultimodalError as exc:
        raise_capability_error(exc)

    return {
        "trip_id": result["trip_id"],
        "itinerary": result["itinerary"],
        "message": result["message"],
    }
