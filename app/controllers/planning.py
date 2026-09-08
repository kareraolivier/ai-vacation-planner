from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import cast
from uuid import UUID

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..schemas.planning import PlanningErrorResponse, PlanningRequest, PlanningResponse
from ..services.planning import PlanningService
from ..ai.rag.embeddings import EmbeddingError
from ..ai.rag.vector_store import VectorStoreError

router = APIRouter(prefix="/planning", tags=["AI Planning"])


@router.post(
    "/",
    response_model=PlanningResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": PlanningErrorResponse, "description": "Invalid request or trip not found"},
        401: {"model": PlanningErrorResponse, "description": "Missing or invalid token"},
        404: {"model": PlanningErrorResponse, "description": "Trip not found"},
        503: {"model": PlanningErrorResponse, "description": "LLM, tool, or knowledge backend unavailable"},
    },
    summary="Generate a vacation plan with the tool-using agent",
    description=(
        "Runs the LangGraph planning agent. The model selects tools (weather, maps, pricing, "
        "travel knowledge) only when they are useful, then composes a day-by-day itinerary. "
        "When trip_id is provided and persist_itinerary is true, the itinerary is stored with "
        "the existing itinerary service."
    ),
)
def plan_vacation(
    request: PlanningRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PlanningService(db)
    user_id: UUID = cast(UUID, current_user.id)
    try:
        return service.plan_trip(user_id, request)
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if str(exc) == "Trip not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc))
    except (RuntimeError, EmbeddingError, VectorStoreError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
