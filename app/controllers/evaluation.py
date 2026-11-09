from fastapi import APIRouter, Depends, status

from ..core.dependencies import get_current_user
from ..models.user import User
from ..ai.eval.evaluator import evaluate_itinerary
from ..schemas.evaluation import EvaluationErrorResponse, EvaluationRequest, EvaluationResult

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


@router.post(
    "/",
    response_model=EvaluationResult,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": EvaluationErrorResponse, "description": "Missing or invalid token"},
        422: {"model": EvaluationErrorResponse, "description": "Invalid evaluation payload"},
    },
    summary="Score an itinerary against a traveler request",
    description=(
        "Runs the same heuristic checks used after planning: relevance to the destination, "
        "completeness vs requested days, structured-output validity, and expected JSON format. "
        "DeepEval wraps these metrics in tests under tests/test_deepeval.py."
    ),
)
def evaluate_generated_itinerary(
    request: EvaluationRequest,
    current_user: User = Depends(get_current_user),
):
    del current_user
    return evaluate_itinerary(
        user_request=request.message,
        destination=request.destination,
        expected_days=request.days,
        itinerary=request.itinerary,
    )
