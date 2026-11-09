import json
import re
from typing import Any, Dict, List, Optional

from ..guardrails.errors import GuardrailError
from ..guardrails.output import itinerary_text, validate_itinerary_structure


def _as_itinerary(actual_output: Any) -> List[Dict[str, Any]]:
    if isinstance(actual_output, list):
        return actual_output
    if isinstance(actual_output, dict) and "days" in actual_output:
        return actual_output.get("days") or actual_output.get("itinerary") or []
    if isinstance(actual_output, dict) and "itinerary" in actual_output:
        return actual_output.get("itinerary") or []
    if isinstance(actual_output, str):
        try:
            parsed = json.loads(actual_output)
        except json.JSONDecodeError:
            return []
        return _as_itinerary(parsed)
    return []


def format_score(actual_output: Any) -> Dict[str, Any]:
    itinerary = _as_itinerary(actual_output)
    try:
        validate_itinerary_structure(itinerary)
        return {"score": 1.0, "reason": "Itinerary matches the expected day/activities JSON"}
    except GuardrailError as exc:
        return {"score": 0.0, "reason": str(exc)}


def completeness_score(actual_output: Any, expected_days: int) -> Dict[str, Any]:
    itinerary = _as_itinerary(actual_output)
    if expected_days <= 0:
        expected_days = 1
    filled = 0
    for day in itinerary:
        activities = [item for item in (day.get("activities") or []) if str(item).strip()]
        if activities:
            filled += 1
    score = min(1.0, filled / expected_days)
    reason = f"{filled}/{expected_days} days have activities"
    return {"score": round(score, 3), "reason": reason}


def relevance_score(actual_output: Any, destination: str, user_request: str = "") -> Dict[str, Any]:
    itinerary = _as_itinerary(actual_output)
    text = itinerary_text(itinerary)
    if not text:
        return {"score": 0.0, "reason": "Empty itinerary"}
    dest = (destination or "").strip().lower()
    hits = 0
    checks = 0
    if dest and dest not in {"unknown", "the destination"}:
        checks += 1
        dest_token = dest.split(",")[0].split()[0]
        if dest in text or dest_token in text:
            hits += 1
    keywords = _request_keywords(user_request)
    for word in keywords:
        checks += 1
        if word in text or word in (user_request or "").lower():
            # Prefer itinerary mention; still give partial credit if the request was honored structurally.
            if word in text:
                hits += 1
            else:
                hits += 0.4
    if checks == 0:
        return {"score": 1.0, "reason": "No destination or request keywords to check"}
    score = max(0.0, min(1.0, hits / checks))
    return {"score": round(score, 3), "reason": f"Matched {hits:.1f}/{checks} relevance checks"}


def validity_score(actual_output: Any, expected_days: int) -> Dict[str, Any]:
    fmt = format_score(actual_output)
    complete = completeness_score(actual_output, expected_days)
    score = round((fmt["score"] * 0.6) + (complete["score"] * 0.4), 3)
    return {
        "score": score,
        "reason": f"Format: {fmt['reason']}. Completeness: {complete['reason']}",
    }


def _request_keywords(user_request: str) -> List[str]:
    if not user_request:
        return []
    stop = {
        "plan",
        "my",
        "a",
        "the",
        "and",
        "include",
        "trip",
        "for",
        "with",
        "this",
        "please",
        "days",
        "day",
    }
    tokens = re.findall(r"[a-zA-Z]{4,}", user_request.lower())
    seen = []
    for token in tokens:
        if token in stop or token in seen:
            continue
        seen.append(token)
        if len(seen) >= 4:
            break
    return seen
