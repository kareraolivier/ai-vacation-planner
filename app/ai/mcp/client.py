import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ...core.config import settings
from .errors import MCPError
from .handlers import TravelToolHandlers
from .server import TravelMCPServer

logger = logging.getLogger(__name__)


class MCPClient(ABC):
    @abstractmethod
    def initialize(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_tools(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError


class InProcessMCPClient(MCPClient):
    """JSON-RPC-shaped MCP client talking to the in-process travel server."""

    def __init__(self, server: Optional[TravelMCPServer] = None, timeout: Optional[float] = None):
        self.server = server or TravelMCPServer()
        self.timeout = timeout or settings.MCP_TIMEOUT
        self._request_id = 0
        self._ready = False

    def initialize(self) -> Dict[str, Any]:
        return self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "vacation-planner", "version": "1.1.0"},
        })

    def list_tools(self) -> List[Dict[str, Any]]:
        self._ensure_ready()
        payload = self._rpc("tools/list")
        return payload.get("tools") or []

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._ensure_ready()
        return self._rpc("tools/call", {"name": name, "arguments": arguments or {}})

    def _ensure_ready(self) -> None:
        if not self._ready:
            self.initialize()
            self._ready = True

    def _rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        started = time.monotonic()
        try:
            result = self.server.handle(request["method"], request["params"])
        except MCPError:
            raise
        except Exception as exc:
            raise MCPError("MCP server is unavailable", code="unavailable") from exc

        elapsed = time.monotonic() - started
        if elapsed > self.timeout:
            raise MCPError("MCP tool timed out", code="timeout")

        response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
        if response.get("error"):
            raise MCPError("MCP server returned an error", code="provider")
        return response["result"]


class FakeMCPClient(MCPClient):
    def __init__(self, tools: Optional[List[Dict[str, Any]]] = None, fail_list: bool = False, fail_call: bool = False):
        self._tools = tools or [
            {
                "name": "mcp_get_weather",
                "description": "MCP weather",
                "inputSchema": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            }
        ]
        self.fail_list = fail_list
        self.fail_call = fail_call
        self.calls: List[Dict[str, Any]] = []

    def initialize(self) -> Dict[str, Any]:
        if self.fail_list:
            raise MCPError("MCP server is unavailable", code="unavailable")
        return {"protocolVersion": "2024-11-05", "serverInfo": {"name": "fake-mcp"}}

    def list_tools(self) -> List[Dict[str, Any]]:
        if self.fail_list:
            raise MCPError("MCP server is unavailable", code="unavailable")
        return list(self._tools)

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.calls.append({"name": name, "arguments": arguments or {}})
        if self.fail_call:
            raise MCPError("MCP tool execution failed", code="provider")
        known = {tool["name"] for tool in self._tools}
        if name not in known:
            raise MCPError(f"MCP tool '{name}' is unavailable", code="unavailable")
        if name == "mcp_get_weather" and not (arguments or {}).get("location"):
            raise MCPError("Invalid tool arguments. Missing: location", code="invalid")
        data = {"ok": True, "tool": name, "arguments": arguments or {}}
        return {
            "content": [{"type": "text", "text": json.dumps(data)}],
            "structuredContent": data,
            "isError": False,
        }


def get_mcp_client(
    handlers: Optional[TravelToolHandlers] = None,
    server: Optional[TravelMCPServer] = None,
) -> MCPClient:
    if not settings.MCP_ENABLED:
        raise MCPError("MCP is disabled", code="unavailable")

    transport = (settings.MCP_TRANSPORT or "inprocess").lower()
    if transport == "fake":
        return FakeMCPClient()
    if transport in {"inprocess", "memory"}:
        return InProcessMCPClient(server=server or TravelMCPServer(handlers=handlers))
    if transport == "stdio":
        raise MCPError("Stdio MCP transport is configured but not attached to this request path", code="config")
    raise MCPError(f"Unsupported MCP transport: {settings.MCP_TRANSPORT}", code="config")
