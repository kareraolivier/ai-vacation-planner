from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from ..repositories.itinerary import ItineraryRepository
from ..repositories.trip import TripRepository
from ..schemas.itinerary import ItineraryCreate
from uuid import UUID

class ItineraryService:
    def __init__(self, db: Session):
        self.itinerary_repo = ItineraryRepository(db)
        self.trip_repo = TripRepository(db)
    
    def create_itinerary(self, user_id: UUID, itinerary_data: ItineraryCreate) -> Optional[dict]:
      
        trip = self.trip_repo.get_user_trip(itinerary_data.trip_id, user_id)
        if not trip:
            return None
        days_list = [day.model_dump() for day in itinerary_data.days]
       
        itinerary = self.itinerary_repo.upsert_itinerary(
            trip_id=itinerary_data.trip_id,
            days=days_list
        )
        
        return {
            "trip_id": itinerary.trip_id,
            "itinerary": itinerary.days,
            "message": "Itinerary created successfully"
        }
    
    def get_trip_itinerary(self, user_id: UUID, trip_id: UUID) -> Optional[Dict[str, Any]]:
        itinerary = self.itinerary_repo.get_trip_itinerary(trip_id, user_id)
        if not itinerary:
            return None
        
        return {
            "trip_id": itinerary.trip_id,
            "itinerary": itinerary.days,
            "created_at": itinerary.created_at,
            "updated_at": itinerary.updated_at
        }