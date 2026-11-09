from typing import Any, Dict, List, Optional

from .errors import MCPError
from .handlers import TravelToolHandlers

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "vacation-travel-tools", "version": "1.0.0"}

TOOL_SPECS: List[Dict[str, Any]] = [
    {
        "name": "mcp_get_weather",
        "description": (
            "MCP weather forecast for a destination. "
            "Use for outdoor plans, packing, or seasonal timing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City or destination name"},
                "days": {"type": "integer", "description": "Forecast days", "minimum": 1, "maximum": 16},
            },
            "required": ["location"],
        },
    },
    {
        "name": "mcp_search_places",
        "description": (
            "MCP maps search for places, neighborhoods, or attractions. "
            "Use when you need locations or nearby points of interest."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Place or attraction search query"},
                "location": {"type": "string", "description": "Optional city or area"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "mcp_add_calendar_event",
        "description": (
            "Add a trip event to the travel calendar through MCP. "
            "Use to save a planned day, reservation, or reminder."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title"},
                "date": {"type": "string", "description": "Event date, ISO preferred"},
                "destination": {"type": "string", "description": "Trip destination"},
                "notes": {"type": "string", "description": "Optional notes"},
            },
            "required": ["title", "date"],
        },
    },
    {
        "name": "mcp_list_calendar_events",
        "description": (
            "List travel calendar events through MCP. "
            "Use to recall saved trip events before composing an itinerary."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string", "description": "Optional destination filter"},
            },
        },
    },
]


class TravelMCPServer:
    """MCP server: initialize, tools/list, and tools/call."""

    def __init__(self, handlers: Optional[TravelToolHandlers] = None):
        self.handlers = handlers or TravelToolHandlers()
        self._initialized = False

    def handle(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        if method == "initialize":
            return self.initialize()
        if method == "tools/list":
            return self.list_tools()
        if method == "tools/call":
            return self.call_tool(params.get("name"), params.get("arguments") or {})
        if method == "ping":
            return {"ok": True}
        raise MCPError(f"Unknown MCP method: {method}", code="invalid")

    def initialize(self) -> Dict[str, Any]:
        self._initialized = True
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": SERVER_INFO,
            "capabilities": {"tools": {"listChanged": False}},
        }

    def list_tools(self) -> Dict[str, Any]:
        return {"tools": list(TOOL_SPECS)}

    def call_tool(self, name: Optional[str], arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not name:
            raise MCPError("Tool name is required", code="invalid")
        spec = next((item for item in TOOL_SPECS if item["name"] == name), None)
        if spec is None:
            raise MCPError(f"MCP tool '{name}' is unavailable", code="unavailable")

        required = spec["inputSchema"].get("required") or []
        missing = [field for field in required if not arguments.get(field)]
        if missing:
            raise MCPError(f"Invalid tool arguments. Missing: {', '.join(missing)}", code="invalid")

        try:
            data = self._dispatch(name, arguments)
        except MCPError:
            raise
        except Exception as exc:
            raise MCPError("MCP tool execution failed", code="provider") from exc

        return {
            "content": [{"type": "text", "text": str(data)}],
            "structuredContent": data,
            "isError": False,
        }

    def _dispatch(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name == "mcp_get_weather":
            return self.handlers.get_weather(
                location=arguments["location"],
                days=int(arguments.get("days") or 5),
            )
        if name == "mcp_search_places":
            return self.handlers.search_places(
                query=arguments["query"],
                location=arguments.get("location"),
                limit=int(arguments.get("limit") or 5),
            )
        if name == "mcp_add_calendar_event":
            return self.handlers.add_calendar_event(
                title=arguments["title"],
                date=arguments["date"],
                destination=arguments.get("destination"),
                notes=arguments.get("notes"),
            )
        if name == "mcp_list_calendar_events":
            return self.handlers.list_calendar_events(destination=arguments.get("destination"))
        raise MCPError(f"MCP tool '{name}' is unavailable", code="unavailable")


def create_fastmcp_server(handlers: Optional[TravelToolHandlers] = None):
    """Optional official FastMCP server for stdio hosts."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise MCPError("Official MCP SDK is not installed", code="config") from exc

    handlers = handlers or TravelToolHandlers()
    mcp = FastMCP("vacation-travel-tools")

    @mcp.tool()
    def mcp_get_weather(location: str, days: int = 5) -> dict:
        return handlers.get_weather(location, days)

    @mcp.tool()
    def mcp_search_places(query: str, location: str = "", limit: int = 5) -> dict:
        return handlers.search_places(query, location or None, limit)

    @mcp.tool()
    def mcp_add_calendar_event(title: str, date: str, destination: str = "", notes: str = "") -> dict:
        return handlers.add_calendar_event(title, date, destination or None, notes or None)

    @mcp.tool()
    def mcp_list_calendar_events(destination: str = "") -> dict:
        return handlers.list_calendar_events(destination or None)

    return mcp
