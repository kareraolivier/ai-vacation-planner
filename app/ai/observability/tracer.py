import threading
import time
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from ...core.config import settings

_current_trace: ContextVar[Optional["TraceRecord"]] = ContextVar("current_trace", default=None)


@dataclass
class TraceRecord:
    name: str
    model: Optional[str] = None
    started_at: float = field(default_factory=time.perf_counter)
    ended_at: Optional[float] = None
    latency_ms: Optional[float] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error: Optional[str] = None
    error_type: Optional[str] = None
    failed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_tokens(self, prompt: int = 0, completion: int = 0) -> None:
        self.prompt_tokens += int(prompt or 0)
        self.completion_tokens += int(completion or 0)
        self.total_tokens = self.prompt_tokens + self.completion_tokens
        if self.model and not self.metadata.get("model"):
            self.metadata["model"] = self.model

    def finish(self, error: Optional[Exception] = None) -> None:
        self.ended_at = time.perf_counter()
        self.latency_ms = round((self.ended_at - self.started_at) * 1000, 2)
        if error is not None:
            self.failed = True
            self.error = str(error)
            self.error_type = error.__class__.__name__

    def snapshot(self) -> Dict[str, Any]:
        latency = self.latency_ms
        if latency is None:
            latency = round((time.perf_counter() - self.started_at) * 1000, 2)
        return {
            "model": self.model or self.metadata.get("model"),
            "latency_ms": latency,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }

    def as_dict(self) -> Dict[str, Any]:
        data = self.snapshot()
        data.update(
            {
                "name": self.name,
                "error": self.error,
                "error_type": self.error_type,
                "failed": self.failed,
                "metadata": self.metadata,
            }
        )
        return data


class ObservabilityStore:
    def __init__(self, max_traces: Optional[int] = None):
        self._lock = threading.Lock()
        self._traces: deque[TraceRecord] = deque(maxlen=max_traces or settings.OBSERVABILITY_MAX_TRACES)
        self.requests = 0
        self.errors = 0
        self.failed_requests = 0
        self.blocked_requests = 0
        self.total_tokens = 0
        self.total_latency_ms = 0.0

    def add(self, trace: TraceRecord) -> None:
        with self._lock:
            self._traces.appendleft(trace)
            self.requests += 1
            self.total_tokens += trace.total_tokens
            self.total_latency_ms += trace.latency_ms or 0
            if trace.failed:
                self.errors += 1
                self.failed_requests += 1
            if (trace.error_type or "") == "GuardrailError" or trace.metadata.get("blocked"):
                self.blocked_requests += 1

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [item.as_dict() for item in list(self._traces)[:limit]]

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            avg_latency = (self.total_latency_ms / self.requests) if self.requests else 0
            return {
                "requests": self.requests,
                "errors": self.errors,
                "failed_requests": self.failed_requests,
                "blocked_requests": self.blocked_requests,
                "total_tokens": self.total_tokens,
                "average_latency_ms": round(avg_latency, 2),
                "service": settings.DD_SERVICE,
                "env": settings.DD_ENV,
                "datadog_enabled": settings.DATADOG_ENABLED,
            }

    def reset(self) -> None:
        with self._lock:
            self._traces.clear()
            self.requests = 0
            self.errors = 0
            self.failed_requests = 0
            self.blocked_requests = 0
            self.total_tokens = 0
            self.total_latency_ms = 0.0


_store = ObservabilityStore()


def get_store() -> ObservabilityStore:
    return _store


def current_trace() -> Optional[TraceRecord]:
    return _current_trace.get()


def record_llm_usage(
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    model: Optional[str] = None,
) -> None:
    trace = current_trace()
    if trace is None:
        return
    if model:
        trace.model = model
    trace.add_tokens(prompt_tokens, completion_tokens)


def extract_usage(response: Any) -> Dict[str, int]:
    usage = getattr(response, "usage", None) or getattr(response, "usage_metadata", None) or {}
    if isinstance(usage, dict):
        prompt = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        completion = usage.get("output_tokens") or usage.get("completion_tokens") or 0
    else:
        prompt = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", 0) or 0
        completion = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", 0) or 0
    return {"prompt_tokens": int(prompt), "completion_tokens": int(completion)}


@contextmanager
def trace_span(name: str, model: Optional[str] = None, **metadata: Any) -> Iterator[TraceRecord]:
    record = TraceRecord(name=name, model=model, metadata=dict(metadata))
    token = _current_trace.set(record)
    try:
        yield record
        record.finish()
    except Exception as exc:
        record.finish(exc)
        raise
    finally:
        _current_trace.reset(token)
        if settings.OBSERVABILITY_ENABLED:
            _store.add(record)
            _emit_datadog(record)


def _emit_datadog(record: TraceRecord) -> None:
    if not settings.DATADOG_ENABLED:
        return
    try:
        from datadog import statsd
    except ImportError:
        return
    tags = [
        f"service:{settings.DD_SERVICE}",
        f"env:{settings.DD_ENV}",
        f"span:{record.name}",
    ]
    if record.model:
        tags.append(f"model:{record.model}")
    statsd.increment("vacation.planner.requests", tags=tags)
    if record.latency_ms is not None:
        statsd.histogram("vacation.planner.latency_ms", record.latency_ms, tags=tags)
    if record.total_tokens:
        statsd.gauge("vacation.planner.tokens", record.total_tokens, tags=tags)
    if record.failed:
        error_tags = tags + [f"error_type:{record.error_type or 'unknown'}"]
        statsd.increment("vacation.planner.errors", tags=error_tags)
        statsd.increment("vacation.planner.failed_requests", tags=error_tags)
