from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ObservabilitySnapshot(BaseModel):
    model: Optional[str] = None
    latency_ms: Optional[float] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ObservabilitySummary(BaseModel):
    requests: int
    errors: int
    failed_requests: int
    blocked_requests: int
    total_tokens: int
    average_latency_ms: float
    service: str
    env: str
    datadog_enabled: bool


class ObservabilityTracesResponse(BaseModel):
    summary: ObservabilitySummary
    traces: List[Dict[str, Any]]
