import re
from typing import FrozenSet, Optional

from .errors import GuardrailError

ALLOWED_TOOLS: FrozenSet[str] = frozenset(
    {
        "get_weather",
        "search_places",
        "estimate_pricing",
        "search_travel_knowledge",
        "mcp_get_weather",
        "mcp_search_places",
        "mcp_add_calendar_event",
        "mcp_list_calendar_events",
    }
)

RESTRICTED_TOOLS: FrozenSet[str] = frozenset(
    {
        "python",
        "shell",
        "bash",
        "sql",
        "http_request",
        "send_email",
        "book_flight",
        "book_hotel",
        "charge_card",
        "delete_user",
        "file_write",
        "os_exec",
    }
)

_UNSUPPORTED_INTENT = re.compile(
    r"\b("
    r"book\s+(my\s+)?(flight|hotel|tickets?)|"
    r"charge\s+(my\s+)?(card|credit\s+card)|"
    r"run\s+(this\s+)?(shell|bash|sql)|"
    r"drop\s+table|"
    r"rm\s+-rf|"
    r"send\s+(an?\s+)?email|"
    r"wire\s+money|"
    r"hack\s+(into|the)|"
    r"exfiltrate"
    r")\b",
    re.I,
)


def is_allowed_tool(name: str) -> bool:
    return name in ALLOWED_TOOLS


def is_restricted_tool(name: str) -> bool:
    return name.lower() in RESTRICTED_TOOLS


def detect_unsupported_intent(text: str) -> Optional[str]:
    if not text:
        return None
    match = _UNSUPPORTED_INTENT.search(text)
    return match.group(0) if match else None


def assert_supported_request(text: str) -> None:
    intent = detect_unsupported_intent(text)
    if intent:
        raise GuardrailError(
            f"Request blocked: unsupported action '{intent}'. "
            "This planner only builds itineraries; it cannot book, pay, or run system commands.",
            code="unsupported_action",
        )


def assert_allowed_tool(name: str) -> None:
    if is_restricted_tool(name) or not is_allowed_tool(name):
        raise GuardrailError(
            f"Blocked unsupported action: {name}",
            code="unsupported_action",
        )
