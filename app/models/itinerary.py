import uuid

from sqlalchemy import Column, Integer, JSON, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
from ..core.types import GUID
class Itinerary(Base):
    __tablename__ = "itineraries"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    days = Column(JSON, nullable=False) 
    trip_id = Column(GUID(), ForeignKey("trips.id"), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    trip = relationship("Trip", back_populates="itineraries")