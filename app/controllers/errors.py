from fastapi import HTTPException, status

from ..ai.guardrails.errors import GuardrailError
from ..ai.mcp.errors import MCPError
from ..ai.providers.base import MultimodalError

_STATUS = {
    "empty": status.HTTP_400_BAD_REQUEST,
    "invalid": status.HTTP_400_BAD_REQUEST,
    "unsupported": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    "too_large": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    "timeout": status.HTTP_503_SERVICE_UNAVAILABLE,
    "provider": status.HTTP_503_SERVICE_UNAVAILABLE,
    "config": status.HTTP_503_SERVICE_UNAVAILABLE,
    "unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
    "external": status.HTTP_503_SERVICE_UNAVAILABLE,
}

_GUARDRAIL_STATUS = {
    "injection": status.HTTP_400_BAD_REQUEST,
    "unsupported_action": status.HTTP_400_BAD_REQUEST,
    "invalid_output": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "incomplete": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "hallucination": status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def raise_capability_error(exc: Exception) -> None:
    if isinstance(exc, (MultimodalError, MCPError)):
        raise HTTPException(
            status_code=_STATUS.get(getattr(exc, "code", "provider"), status.HTTP_503_SERVICE_UNAVAILABLE),
            detail=str(exc),
        )
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service is temporarily unavailable")


def raise_planning_error(exc: Exception) -> None:
    if isinstance(exc, GuardrailError):
        raise HTTPException(
            status_code=_GUARDRAIL_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
            detail=str(exc),
        )
    if isinstance(exc, ValueError):
        status_code = status.HTTP_404_NOT_FOUND if str(exc) == "Trip not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
