from typing import Any, Dict, List, Optional

from ...core.config import settings
from .actions import assert_supported_request
from .errors import GuardrailError
from .injection import assert_not_injection
from .output import (
    assert_not_placeholder,
    assert_relevant_itinerary,
    validate_itinerary_structure,
)


def check_input_guardrails(message: str) -> None:
    if not settings.GUARDRAILS_ENABLED:
        return
    assert_not_injection(message)
    assert_supported_request(message)


def check_output_guardrails(
    itinerary: List[Dict[str, Any]],
    destination: str,
    expected_days: int,
) -> List[Dict[str, Any]]:
    if not settings.GUARDRAILS_ENABLED:
        return itinerary
    days = validate_itinerary_structure(itinerary)
    if settings.GUARDRAILS_REJECT_INVALID:
        assert_not_placeholder(days)
        assert_relevant_itinerary(days, destination)
    return days


def guardrail_code(exc: Exception) -> Optional[str]:
    if isinstance(exc, GuardrailError):
        return exc.code
    return None
