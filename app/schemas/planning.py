from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID

from .itinerary import DayActivity


class PlanningRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Natural-language planning request, e.g. 'Plan my Paris trip and include weather-friendly activities.'",
    )
    trip_id: Optional[UUID] = Field(None, description="Optional existing trip to plan for and persist against")
    destination: Optional[str] = Field(None, min_length=1, max_length=100)
    days: Optional[int] = Field(None, ge=1, le=365)
    budget: Optional[float] = Field(None, gt=0)
    trip_style: Optional[str] = Field(None, pattern="^(budget|luxury|family|adventure)$")
    persist_itinerary: bool = Field(
        True,
        description="When trip_id is provided, save the generated itinerary using the existing itinerary API contract",
    )


class PlanningResponse(BaseModel):
    trip_id: Optional[UUID] = None
    destination: str
    summary: str
    itinerary: List[Dict[str, Any]]
    tools_used: List[str]
    warnings: List[str] = []
    message: str


class GeneratedItinerary(BaseModel):
    summary: str = Field(..., description="Short overview of the recommended trip")
    days: List[DayActivity]
    notes: List[str] = Field(default_factory=list, description="Caveats or assumptions")


class PlanningErrorResponse(BaseModel):
    detail: str
