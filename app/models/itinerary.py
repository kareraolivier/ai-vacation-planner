import uuid

from sqlalchemy import Column, Integer, JSON, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
class Itinerary(Base):
    __tablename__ = "itineraries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    days = Column(JSON, nullable=False) 
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    trip = relationship("Trip", back_populates="itineraries")