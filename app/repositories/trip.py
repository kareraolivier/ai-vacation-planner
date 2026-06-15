from typing import List, Optional
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models.trip import Trip
from uuid import UUID


class TripRepository(BaseRepository[Trip]):
    def __init__(self, db: Session):
        super().__init__(Trip, db)

    def get_user_trips(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Trip]:
        return self.db.query(Trip).filter(Trip.user_id == user_id).order_by(Trip.created_at.desc()).offset(skip).limit(limit).all()

    def get_user_trip(self, trip_id: UUID, user_id: UUID) -> Optional[Trip]:
        return self.db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()

    def delete_user_trip(self, trip_id: UUID, user_id: UUID) -> bool:
        trip = self.get_user_trip(trip_id, user_id)
        if trip:
            self.db.delete(trip)
            self.db.commit()
            return True
        return False
