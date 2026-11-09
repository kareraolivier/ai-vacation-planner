from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluationScores(BaseModel):
    relevance: float
    completeness: float
    validity: float
    format: float


class EvaluationResult(BaseModel):
    relevant: bool
    complete: bool
    valid: bool
    follows_format: bool
    overall_score: float
    passed: bool
    scores: EvaluationScores
    reasons: Dict[str, str]


class EvaluationRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="Original traveler request")
    destination: str = Field(..., min_length=1, max_length=100)
    days: int = Field(..., ge=1, le=365)
    itinerary: List[Dict[str, Any]] = Field(..., description="Generated itinerary days to score")


class EvaluationErrorResponse(BaseModel):
    detail: str
