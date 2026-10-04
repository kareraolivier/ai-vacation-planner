from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..ai.mcp.client import get_mcp_client
from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..schemas.multimodal import (
    MCPToolCallRequest,
    MCPToolCallResponse,
    MCPToolListResponse,
    MultimodalErrorResponse,
)
from .errors import raise_capability_error

router = APIRouter(prefix="/mcp", tags=["MCP"])

_ERROR_RESPONSES = {
    400: {"model": MultimodalErrorResponse, "description": "Invalid tool arguments"},
    401: {"model": MultimodalErrorResponse, "description": "Missing or invalid token"},
    503: {"model": MultimodalErrorResponse, "description": "MCP server or tool unavailable"},
}


@router.get(
    "/tools",
    response_model=MCPToolListResponse,
    responses=_ERROR_RESPONSES,
    summary="Discover MCP travel tools",
    description="Lists tools exposed by the Vacation Planner MCP server (weather, maps, calendar).",
)
def list_mcp_tools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user, db
    try:
        tools = get_mcp_client().list_tools()
    except Exception as exc:
        raise_capability_error(exc)
    return MCPToolListResponse(tools=tools, message="MCP tools discovered")


@router.post(
    "/tools/{tool_name}",
    response_model=MCPToolCallResponse,
    responses=_ERROR_RESPONSES,
    summary="Invoke an MCP travel tool",
    description="Calls a discovered MCP tool. The planning agent uses the same client.",
)
def call_mcp_tool(
    tool_name: str,
    request: MCPToolCallRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user, db
    try:
        result = get_mcp_client().call_tool(tool_name, request.arguments)
    except Exception as exc:
        raise_capability_error(exc)
    return MCPToolCallResponse(name=tool_name, result=result, message="MCP tool executed")
