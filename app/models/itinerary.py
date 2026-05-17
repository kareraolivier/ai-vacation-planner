from sqlalchemy import Column, Integer, JSON, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base

class Itinerary(Base):
    __tablename__ = "itineraries"
    
    id = Column(Integer, primary_key=True, index=True)
    days = Column(JSON, nullable=False)  # Stores list of day activities
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    trip = relationship("Trip", back_populates="itineraries")