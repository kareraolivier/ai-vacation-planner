from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.itinerary import ItineraryService
from ..schemas.itinerary import GenerateAIRequest, ItineraryCreate, ItineraryOutput
from typing import cast
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
    summary="Generate an itinerary with Claude, using retrieved travel knowledge when available",
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
        result = ItineraryService(db).generate_ai_itinerary(user_id, trip_id, extra)
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
