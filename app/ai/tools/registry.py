from typing import Dict, List, Optional

from langchain_core.tools import BaseTool

from ...services.knowledge import KnowledgeService
from ..providers.base import MapsProvider, PricingProvider, WeatherProvider
from .base import AgentTool
from .knowledge import KnowledgeTool
from .maps import MapsTool
from .pricing import PricingTool
from .weather import WeatherTool


class ToolRegistry:
    def __init__(
        self,
        knowledge_service: KnowledgeService,
        weather_provider: Optional[WeatherProvider] = None,
        maps_provider: Optional[MapsProvider] = None,
        pricing_provider: Optional[PricingProvider] = None,
    ):
        tools = [
            WeatherTool(provider=weather_provider) if weather_provider else WeatherTool(),
            MapsTool(provider=maps_provider) if maps_provider else MapsTool(),
            PricingTool(provider=pricing_provider) if pricing_provider else PricingTool(),
            KnowledgeTool(knowledge_service),
        ]
        self._tools: Dict[str, AgentTool] = {tool.name: tool for tool in tools}

    def get(self, name: str) -> Optional[AgentTool]:
        return self._tools.get(name)

    def all(self) -> List[AgentTool]:
        return list(self._tools.values())

    def langchain_tools(self) -> List[BaseTool]:
        return [tool.as_langchain_tool() for tool in self._tools.values()]
