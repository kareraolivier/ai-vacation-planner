import uuid
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
from ..core.types import GUID

class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    destination = Column(String, nullable=False)
    days = Column(Integer, nullable=False)
    budget = Column(Float, nullable=False)
    trip_style = Column(String, nullable=False)  
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="trips")
    itineraries = relationship("Itinerary", back_populates="trip", cascade="all, delete-orphan")