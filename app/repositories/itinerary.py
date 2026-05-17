from typing import Optional
from sqlalchemy.orm import Session
from .base_repository import BaseRepository
from ..models.itinerary import Itinerary
from ..models.trip import Trip

class ItineraryRepository(BaseRepository[Itinerary]):
    def __init__(self, db: Session):
        super().__init__(Itinerary, db)
    
    def get_by_trip(self, trip_id: int) -> Optional[Itinerary]:
        return self.get_by(trip_id=trip_id)
    
    def get_trip_itinerary(self, trip_id: int, user_id: int) -> Optional[Itinerary]:
        return self.db.query(Itinerary).join(Trip).filter(
            Itinerary.trip_id == trip_id,
            Trip.user_id == user_id
        ).first()
    
    def upsert_itinerary(self, trip_id: int, days: list) -> Itinerary:
        existing = self.get_by_trip(trip_id)
        if existing:
            return self.update(existing.id, days=days)
        return self.create(trip_id=trip_id, days=days)