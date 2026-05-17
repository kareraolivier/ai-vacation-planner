from typing import List, Optional
from sqlalchemy.orm import Session
from ..repositories.trip_repository import TripRepository
from ..schemas.trip import TripCreate, TripUpdate

class TripService:
    def __init__(self, db: Session):
        self.trip_repo = TripRepository(db)
    
    def create_trip(self, user_id: int, trip_data: TripCreate) -> dict:
        trip = self.trip_repo.create(
            user_id=user_id,
            destination=trip_data.destination,
            days=trip_data.days,
            budget=trip_data.budget,
            trip_style=trip_data.trip_style
        )
        
        return {
            "id": trip.id,
            "destination": trip.destination,
            "days": trip.days,
            "budget": trip.budget,
            "trip_style": trip.trip_style,
            "message": "Trip created successfully"
        }
    
    def get_user_trips(self, user_id: int) -> List[TripRepository.model]:
        return self.trip_repo.get_user_trips(user_id)
    
    def get_user_trip(self, user_id: int, trip_id: int) -> Optional[TripRepository.model]:
        return self.trip_repo.get_user_trip(trip_id, user_id)
    
    def update_trip(self, user_id: int, trip_id: int, trip_data: TripUpdate) -> Optional[dict]:
        trip = self.trip_repo.get_user_trip(trip_id, user_id)
        if not trip:
            return None
        
        update_data = trip_data.model_dump(exclude_unset=True)
        updated_trip = self.trip_repo.update(trip_id, **update_data)
        
        return {
            "id": updated_trip.id,
            "destination": updated_trip.destination,
            "days": updated_trip.days,
            "budget": updated_trip.budget,
            "trip_style": updated_trip.trip_style,
            "message": "Trip updated successfully"
        }
    
    def delete_trip(self, user_id: int, trip_id: int) -> bool:
        return self.trip_repo.delete_user_trip(trip_id, user_id)