from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID


class DayActivity(BaseModel):
    day: int = Field(..., ge=1)
    activities: List[str] = Field(..., min_length=1)


class ItineraryCreate(BaseModel):
    trip_id: UUID
    days: Optional[List[DayActivity]] = None


class ItineraryResponse(BaseModel):
    id: UUID
    trip_id: UUID
    days: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItineraryOutput(BaseModel):
    trip_id: UUID
    itinerary: List[Dict[str, Any]]
    message: str


class GenerateAIRequest(BaseModel):
    message: Optional[str] = Field(
        None,
        max_length=4000,
        description="Optional extra request, e.g. include weather-friendly activities",
    )
