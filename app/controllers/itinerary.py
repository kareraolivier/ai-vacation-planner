from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import cast
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.itinerary import ItineraryService
from ..schemas.itinerary import ItineraryCreate, ItineraryOutput
from typing import List, cast
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


@router.post("/{trip_id}/generate-ai", response_model=ItineraryOutput, status_code=status.HTTP_201_CREATED)
def generate_ai_itinerary(
    trip_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    itinerary = ItineraryService(db)
    user_id: UUID = cast(UUID, current_user.id)

    itinerary_data = ItineraryCreate(trip_id=trip_id, days=None)
    result = itinerary.create_itinerary(
        user_id=user_id,
        itinerary_data=itinerary_data,
        use_ai=True
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    return result
