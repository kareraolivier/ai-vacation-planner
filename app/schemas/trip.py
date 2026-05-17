from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from uuid import UUID
class TripCreate(BaseModel):
    destination: str = Field(..., min_length=1, max_length=100)
    days: int = Field(..., ge=1, le=365)
    budget: float = Field(..., gt=0)
    trip_style: str = Field(..., pattern="^(budget|luxury|family|adventure)$")
    
    @field_validator('destination')
    def validate_destination(cls, v):
        return v.title()

class TripUpdate(BaseModel):
    destination: Optional[str] = Field(None, min_length=1, max_length=100)
    days: Optional[int] = Field(None, ge=1, le=365)
    budget: Optional[float] = Field(None, gt=0)
    trip_style: Optional[str] = Field(None, pattern="^(budget|luxury|family|adventure)$")

class TripResponse(BaseModel):
    id: UUID
    destination: str
    days: int
    budget: float
    trip_style: str
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TripCreateResponse(BaseModel):
    id: UUID
    destination: str
    days: int
    budget: float
    trip_style: str
    message: str 