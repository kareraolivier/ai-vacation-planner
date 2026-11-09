import re
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from ...schemas.itinerary import DayActivity
from .errors import GuardrailError

_KNOWN_CITIES = {
    "paris",
    "tokyo",
    "barcelona",
    "london",
    "rome",
    "new york",
    "kyoto",
    "lisbon",
    "berlin",
    "madrid",
    "amsterdam",
    "dubai",
    "sydney",
}


def itinerary_text(itinerary: List[Dict[str, Any]]) -> str:
    parts = []
    for day in itinerary or []:
        parts.append(str(day.get("day") or ""))
        parts.extend(str(item) for item in (day.get("activities") or []))
    return " ".join(parts).lower()


def validate_itinerary_structure(itinerary: Any) -> List[Dict[str, Any]]:
    if not isinstance(itinerary, list) or not itinerary:
        raise GuardrailError(
            "Invalid itinerary: expected a non-empty list of days",
            code="invalid_output",
        )
    days: List[Dict[str, Any]] = []
    for index, item in enumerate(itinerary):
        if not isinstance(item, dict):
            raise GuardrailError("Invalid itinerary: each day must be an object", code="invalid_output")
        try:
            parsed = DayActivity.model_validate(
                {
                    "day": item.get("day", index + 1),
                    "activities": item.get("activities") or [],
                }
            )
        except ValidationError as exc:
            raise GuardrailError(f"Invalid itinerary day: {exc}", code="invalid_output") from exc
        if not parsed.activities or not all(str(activity).strip() for activity in parsed.activities):
            raise GuardrailError("Invalid itinerary: each day needs at least one activity", code="invalid_output")
        days.append(parsed.model_dump())
    return days


def assert_complete_itinerary(itinerary: List[Dict[str, Any]], expected_days: int) -> None:
    if len(itinerary) < expected_days:
        raise GuardrailError(
            f"Incomplete itinerary: expected {expected_days} days, got {len(itinerary)}",
            code="incomplete",
        )


def assert_relevant_itinerary(itinerary: List[Dict[str, Any]], destination: str) -> None:
    if not destination or destination.lower() in {"unknown", "the destination"}:
        return
    text = itinerary_text(itinerary)
    dest = destination.strip().lower()
    dest_token = dest.split(",")[0].split()[0]
    mentions_destination = dest in text or dest_token in text
    other_cities = [city for city in _KNOWN_CITIES if city != dest and city in text]
    if other_cities and not mentions_destination:
        raise GuardrailError(
            f"Itinerary looks unrelated to {destination}",
            code="hallucination",
        )


_PLACEHOLDER = re.compile(r"\b(todo|tbd|lorem ipsum|activity\s*\d+)\b", re.I)


def assert_not_placeholder(itinerary: List[Dict[str, Any]]) -> None:
    text = itinerary_text(itinerary)
    if _PLACEHOLDER.search(text):
        raise GuardrailError("Itinerary contains placeholder content", code="invalid_output")
