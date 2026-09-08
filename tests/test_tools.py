import json

import pytest
from pydantic import ValidationError

from app.ai.providers.base import ProviderError
from app.ai.tools.maps import MapsTool, MapsToolInput
from app.ai.tools.pricing import PricingTool, PricingToolInput
from app.ai.tools.weather import WeatherTool, WeatherToolInput


class FakeWeather:
    def get_forecast(self, location, days):
        return {"location": location, "days": [{"date": "2026-08-23", "temperature_max_c": 24}]}


class BrokenWeather:
    def get_forecast(self, location, days):
        raise ProviderError("weather", "weather API unavailable")


class FakeMaps:
    def search_places(self, query, location, limit):
        return {"query": query, "places": [{"name": "Louvre"}]}


class FakePricing:
    def estimate(self, destination, days, budget, trip_style, travelers):
        return {"destination": destination, "estimate": 900}


def test_weather_tool_validates_input():
    with pytest.raises(ValidationError):
        WeatherToolInput(location="", days=5)
    with pytest.raises(ValidationError):
        WeatherToolInput(location="Paris", days=0)


def test_weather_tool_success():
    tool = WeatherTool(provider=FakeWeather())
    result = json.loads(tool.run(location="Paris", days=3))
    assert result["success"] is True
    assert result["data"]["location"] == "Paris"


def test_weather_tool_provider_failure_is_soft():
    tool = WeatherTool(provider=BrokenWeather())
    result = json.loads(tool.run(location="Paris", days=3))
    assert result["success"] is False
    assert "unavailable" in result["error"]


def test_maps_and_pricing_tools_success():
    maps = json.loads(MapsTool(provider=FakeMaps()).run(query="museums", location="Paris"))
    pricing = json.loads(PricingTool(provider=FakePricing()).run(destination="Paris", days=4, budget=1200))
    assert maps["success"] is True
    assert pricing["success"] is True


def test_pricing_tool_validates_days():
    with pytest.raises(ValidationError):
        PricingToolInput(destination="Paris", days=0)
