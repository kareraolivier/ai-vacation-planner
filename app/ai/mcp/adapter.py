import logging
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, create_model

from ..tools.base import AgentTool, ToolResult
from .client import MCPClient
from .errors import MCPError

logger = logging.getLogger(__name__)


class MCPAgentTool(AgentTool):
    """LangGraph-facing wrapper around one discovered MCP tool."""

    def __init__(self, spec: Dict[str, Any], client: MCPClient):
        self.name = spec["name"]
        self.description = spec.get("description") or spec["name"]
        self.args_schema = _schema_to_model(self.name, spec.get("inputSchema") or {})
        self.client = client

    def execute(self, params: BaseModel) -> ToolResult:
        arguments = params.model_dump(exclude_none=True)
        try:
            payload = self.client.call_tool(self.name, arguments)
        except MCPError as exc:
            logger.warning("MCP tool %s failed: %s", self.name, exc)
            return ToolResult(success=False, error=str(exc))

        data = payload.get("structuredContent")
        if data is None:
            content = payload.get("content") or []
            if content and isinstance(content[0], dict):
                data = content[0].get("text")
        if payload.get("isError"):
            return ToolResult(success=False, error=str(data or "MCP tool failed"))
        return ToolResult(success=True, data=data)


def discover_mcp_tools(client: MCPClient) -> List[AgentTool]:
    try:
        specs = client.list_tools()
    except MCPError:
        raise
    except Exception as exc:
        raise MCPError("MCP server is unavailable", code="unavailable") from exc
    return [MCPAgentTool(spec, client) for spec in specs if spec.get("name")]


def _schema_to_model(name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    fields: Dict[str, Any] = {}
    for key, spec in properties.items():
        annotation = _json_type(spec.get("type"))
        description = spec.get("description")
        if key in required:
            fields[key] = (annotation, Field(..., description=description))
        else:
            fields[key] = (Optional[annotation], Field(None, description=description))
    model_name = "".join(part.capitalize() for part in name.replace("-", "_").split("_")) + "Input"
    if not fields:
        return create_model(model_name)
    return create_model(model_name, **fields)


def _json_type(type_name: Optional[str]):
    return {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "object": dict,
        "array": list,
    }.get(type_name or "string", str)
