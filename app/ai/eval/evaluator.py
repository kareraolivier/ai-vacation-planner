from typing import Any, Dict, List, Optional

from ...core.config import settings
from .metrics import completeness_score, format_score, relevance_score, validity_score


class ItineraryEvaluator:
    """Heuristic quality checks used at request time and in DeepEval tests."""

    def evaluate(
        self,
        user_request: str,
        destination: str,
        expected_days: int,
        itinerary: List[Dict[str, Any]],
        minimum: Optional[float] = None,
    ) -> Dict[str, Any]:
        format_result = format_score(itinerary)
        complete_result = completeness_score(itinerary, expected_days)
        relevance_result = relevance_score(itinerary, destination, user_request)
        validity_result = validity_score(itinerary, expected_days)
        overall = round(
            (
                format_result["score"]
                + complete_result["score"]
                + relevance_result["score"]
                + validity_result["score"]
            )
            / 4,
            3,
        )
        threshold = settings.EVALUATION_MIN_SCORE if minimum is None else minimum
        passed = (
            overall >= threshold
            and relevance_result["score"] >= threshold
            and complete_result["score"] >= threshold
            and format_result["score"] >= 1.0
        )
        return {
            "relevant": relevance_result["score"] >= threshold,
            "complete": complete_result["score"] >= threshold,
            "valid": validity_result["score"] >= threshold,
            "follows_format": format_result["score"] >= 1.0,
            "overall_score": overall,
            "passed": passed,
            "scores": {
                "relevance": relevance_result["score"],
                "completeness": complete_result["score"],
                "validity": validity_result["score"],
                "format": format_result["score"],
            },
            "reasons": {
                "relevance": relevance_result["reason"],
                "completeness": complete_result["reason"],
                "validity": validity_result["reason"],
                "format": format_result["reason"],
            },
        }


def evaluate_itinerary(
    user_request: str,
    destination: str,
    expected_days: int,
    itinerary: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return ItineraryEvaluator().evaluate(
        user_request=user_request,
        destination=destination,
        expected_days=expected_days,
        itinerary=itinerary,
    )
