from typing import Optional
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models.itinerary import Itinerary
from ..models.trip import Trip
from uuid import UUID

class ItineraryRepository(BaseRepository[Itinerary]):
    def __init__(self, db: Session):
        super().__init__(Itinerary, db)
    
    def get_by_trip(self, trip_id: UUID) -> Optional[Itinerary]:
        return self.get_by(trip_id=trip_id)
    
    def get_trip_itinerary(self, trip_id: UUID, user_id: UUID) -> Optional[Itinerary]:
        return self.db.query(Itinerary).join(Trip).filter(
            Itinerary.trip_id == trip_id,
            Trip.user_id == user_id
        ).first()
    
    def upsert_itinerary(self, trip_id: UUID, days: list) -> Itinerary:
        existing = self.get_by_trip(trip_id)
        if existing:
            return self.update(existing.id.value, days=days)
        return self.create(trip_id=trip_id, days=days)

    def delete_by_trip(self, trip_id: UUID) -> bool:
        existing = self.get_by_trip(trip_id)
        if existing:
            self.delete(existing.id.value)
            return True
        return False