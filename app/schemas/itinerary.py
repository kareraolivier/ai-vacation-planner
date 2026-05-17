from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime

class DayActivity(BaseModel):
    day: int = Field(..., ge=1)
    activities: List[str] = Field(..., min_length=1)

class ItineraryCreate(BaseModel):
    trip_id: int
    days: List[DayActivity]

class ItineraryResponse(BaseModel):
    id: int
    trip_id: int
    days: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ItineraryOutput(BaseModel):
    trip_id: int
    itinerary: List[Dict[str, Any]]
    message: str = "Itinerary created successfully"