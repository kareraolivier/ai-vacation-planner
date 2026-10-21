from fastapi import HTTPException, status

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


def raise_capability_error(exc: Exception) -> None:
    if isinstance(exc, (MultimodalError, MCPError)):
        raise HTTPException(
            status_code=_STATUS.get(getattr(exc, "code", "provider"), status.HTTP_503_SERVICE_UNAVAILABLE),
            detail=str(exc),
        )
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service is temporarily unavailable")
