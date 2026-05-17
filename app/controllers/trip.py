from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.trip_service import TripService
from ..schemas.trip import TripCreate, TripUpdate, TripResponse, TripCreateResponse
from typing import List

router = APIRouter(prefix="/trips", tags=["Trips"])

@router.post("/", response_model=TripCreateResponse, status_code=status.HTTP_201_CREATED)
def create_trip(
    trip_data: TripCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip_service = TripService(db)
    return trip_service.create_trip(current_user.id, trip_data)

@router.get("/", response_model=List[TripResponse])
def get_user_trips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    trip_service = TripService(db)
    return trip_service.get_user_trips(current_user.id)

@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip_service = TripService(db)
    trip = trip_service.get_user_trip(current_user.id, trip_id)
    
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    return trip

@router.put("/{trip_id}", response_model=TripCreateResponse)
def update_trip(
    trip_id: int,
    trip_data: TripUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip_service = TripService(db)
    updated_trip = trip_service.update_trip(current_user.id, trip_id, trip_data)
    
    if not updated_trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    return updated_trip

@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip_service = TripService(db)
    deleted = trip_service.delete_trip(current_user.id, trip_id)
    
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")