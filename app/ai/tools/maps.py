from typing import Optional

from pydantic import BaseModel, Field

from ..providers.base import MapsProvider
from ..providers.maps import get_maps_provider
from .base import AgentTool, ToolResult


class MapsToolInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="Place or attraction search query")
    location: Optional[str] = Field(None, max_length=120, description="Optional city or area to bias the search")
    limit: int = Field(5, ge=1, le=10, description="Maximum number of places to return")


class MapsTool(AgentTool):
    name = "search_places"
    description = (
        "Search maps for places, neighborhoods, or attractions. "
        "Use when you need locations, coordinates, or nearby points of interest."
    )
    args_schema = MapsToolInput

    def __init__(self, provider: MapsProvider = None):
        self.provider = provider or get_maps_provider()

    def execute(self, params: MapsToolInput) -> ToolResult:
        data = self.provider.search_places(params.query, params.location, params.limit)
        return ToolResult(success=True, data=data)
