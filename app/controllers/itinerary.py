from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.itinerary_service import ItineraryService
from ..schemas.itinerary import ItineraryCreate, ItineraryOutput

router = APIRouter(prefix="/itineraries", tags=["Itineraries"])

@router.post("/", response_model=ItineraryOutput, status_code=status.HTTP_201_CREATED)
def create_itinerary(
    itinerary_data: ItineraryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    itinerary_service = ItineraryService(db)
    result = itinerary_service.create_itinerary(current_user.id, itinerary_data)
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    return result

@router.get("/{trip_id}", response_model=ItineraryOutput)
def get_trip_itinerary(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    itinerary_service = ItineraryService(db)
    result = itinerary_service.get_trip_itinerary(current_user.id, trip_id)
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    
    return {
        "trip_id": result["trip_id"],
        "itinerary": result["itinerary"],
        "message": "Itinerary retrieved successfully"
    }