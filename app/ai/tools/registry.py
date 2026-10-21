import logging
from typing import Dict, List, Optional

from langchain_core.tools import BaseTool

from ...core.config import settings
from ...services.knowledge import KnowledgeService
from ..mcp.adapter import discover_mcp_tools
from ..mcp.client import MCPClient, get_mcp_client
from ..mcp.errors import MCPError
from ..providers.base import MapsProvider, PricingProvider, WeatherProvider
from .base import AgentTool
from .knowledge import KnowledgeTool
from .maps import MapsTool
from .pricing import PricingTool
from .weather import WeatherTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(
        self,
        knowledge_service: KnowledgeService,
        weather_provider: Optional[WeatherProvider] = None,
        maps_provider: Optional[MapsProvider] = None,
        pricing_provider: Optional[PricingProvider] = None,
        mcp_client: Optional[MCPClient] = None,
        include_mcp: Optional[bool] = None,
    ):
        tools = [
            WeatherTool(provider=weather_provider) if weather_provider else WeatherTool(),
            MapsTool(provider=maps_provider) if maps_provider else MapsTool(),
            PricingTool(provider=pricing_provider) if pricing_provider else PricingTool(),
            KnowledgeTool(knowledge_service),
        ]
        self._tools: Dict[str, AgentTool] = {tool.name: tool for tool in tools}
        self.mcp_warning: Optional[str] = None
        should_include_mcp = settings.MCP_ENABLED if include_mcp is None else include_mcp
        if should_include_mcp:
            try:
                client = mcp_client or get_mcp_client()
                for tool in discover_mcp_tools(client):
                    self._tools[tool.name] = tool
            except MCPError as exc:
                logger.warning("MCP tools unavailable: %s", exc)
                self.mcp_warning = str(exc)

    def get(self, name: str) -> Optional[AgentTool]:
        return self._tools.get(name)

    def all(self) -> List[AgentTool]:
        return list(self._tools.values())

    def langchain_tools(self) -> List[BaseTool]:
        return [tool.as_langchain_tool() for tool in self._tools.values()]
