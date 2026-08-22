from pydantic import BaseModel, Field

from ..providers.base import WeatherProvider
from ..providers.weather import get_weather_provider
from .base import AgentTool, ToolResult


class WeatherToolInput(BaseModel):
    location: str = Field(..., min_length=1, max_length=120, description="City or destination name")
    days: int = Field(5, ge=1, le=16, description="Number of forecast days")


class WeatherTool(AgentTool):
    name = "get_weather"
    description = (
        "Get a multi-day weather forecast for a destination. "
        "Use when the traveler mentions weather, outdoor plans, packing, or seasonal timing."
    )
    args_schema = WeatherToolInput

    def __init__(self, provider: WeatherProvider = None):
        self.provider = provider or get_weather_provider()

    def execute(self, params: WeatherToolInput) -> ToolResult:
        data = self.provider.get_forecast(params.location, params.days)
        return ToolResult(success=True, data=data)
