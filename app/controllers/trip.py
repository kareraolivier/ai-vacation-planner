from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.trip import TripService
from ..schemas.trip import TripCreate, TripUpdate, TripResponse, TripCreateResponse
from typing import List, cast
from uuid import UUID

router = APIRouter(prefix="/trips", tags=["Trips"])

@router.post("/", response_model=TripCreateResponse, status_code=status.HTTP_201_CREATED)
def create_trip(
    trip_data: TripCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip = TripService(db)
    user_id: UUID = cast(UUID, current_user.id)
    return trip.create_trip(user_id, trip_data)

@router.get("/", response_model=List[TripResponse], status_code=status.HTTP_200_OK)
def get_user_trips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    trip = TripService(db)
    user_id: UUID = cast(UUID, current_user.id)
    return trip.get_user_trips(user_id)

@router.get("/{trip_id}", response_model=TripResponse, status_code=status.HTTP_200_OK)
def get_trip(
    trip_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip = TripService(db)
    user_id: UUID = cast(UUID, current_user.id)
    trip = trip.get_user_trip(user_id, trip_id)

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    return trip

@router.put("/{trip_id}", response_model=TripCreateResponse, status_code=status.HTTP_200_OK)
def update_trip(
    trip_id: UUID,
    trip_data: TripUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip = TripService(db)
    user_id: UUID = cast(UUID, current_user.id)
    updated_trip = trip.update_trip(user_id, trip_id, trip_data)
    
    if not updated_trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    return updated_trip

@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(
    trip_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip = TripService(db)
    user_id: UUID = cast(UUID, current_user.id)
    deleted = trip.delete_trip(user_id, trip_id)
    
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")