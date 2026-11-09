import re
from typing import List, Optional, Tuple

from .errors import GuardrailError

_INJECTION_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("ignore_instructions", re.compile(r"\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b", re.I)),
    ("disregard_rules", re.compile(r"\bdisregard\s+(the\s+)?(above|previous|system)\b", re.I)),
    ("reveal_prompt", re.compile(r"\b(reveal|print|show|dump)\s+(your\s+)?(system\s+)?(prompt|instructions)\b", re.I)),
    ("role_hijack", re.compile(r"\b(you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(unrestricted|jailbroken|dan|a\s+hacker)\b", re.I)),
    ("jailbreak", re.compile(r"\b(jailbreak|dan\s+mode|developer\s+mode|god\s+mode)\b", re.I)),
    ("new_system", re.compile(r"(<\|im_start\|>|```system\b|system\s*:\s*you\s+are)", re.I)),
    ("tool_override", re.compile(r"\b(call\s+every\s+tool|override\s+tools?|disable\s+guardrails?)\b", re.I)),
    ("secret_exfil", re.compile(r"\b(api[_-]?key|secret[_-]?key|password)\b.{0,40}\b(print|reveal|output|leak)\b", re.I)),
]


def detect_prompt_injection(text: str) -> Optional[str]:
    if not text or not text.strip():
        return None
    for code, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return code
    return None


def assert_not_injection(text: str) -> None:
    code = detect_prompt_injection(text)
    if code:
        raise GuardrailError(
            "Request blocked: prompt injection attempt detected",
            code="injection",
        )
