import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ...core.config import settings


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Attach per-request latency without double-counting AI traces."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.OBSERVABILITY_ENABLED:
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        request.state.observability_latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return response
