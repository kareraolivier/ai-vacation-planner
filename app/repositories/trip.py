from typing import List, Optional
from sqlalchemy.orm import Session
from .base_repository import BaseRepository
from ..models.trip import Trip

class TripRepository(BaseRepository[Trip]):
    def __init__(self, db: Session):
        super().__init__(Trip, db)
    
    def get_user_trips(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Trip]:
        return self.db.query(Trip).filter(Trip.user_id == user_id).offset(skip).limit(limit).all()
    
    def get_user_trip(self, trip_id: int, user_id: int) -> Optional[Trip]:
        return self.db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    
    def delete_user_trip(self, trip_id: int, user_id: int) -> bool:
        trip = self.get_user_trip(trip_id, user_id)
        if trip:
            self.db.delete(trip)
            self.db.commit()
            return True
        return False