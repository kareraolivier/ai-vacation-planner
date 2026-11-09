from typing import Any, Dict, Optional

from ..providers.base import MapsProvider, ProviderError, WeatherProvider
from ..providers.maps import get_maps_provider
from ..providers.weather import get_weather_provider
from .calendar import TravelCalendarStore, travel_calendar
from .errors import MCPError


class TravelToolHandlers:
    """Business handlers behind MCP tools. Providers stay swappable."""

    def __init__(
        self,
        weather_provider: Optional[WeatherProvider] = None,
        maps_provider: Optional[MapsProvider] = None,
        calendar: Optional[TravelCalendarStore] = None,
    ):
        self._weather_provider = weather_provider
        self._maps_provider = maps_provider
        self.calendar = calendar or travel_calendar

    @property
    def weather_provider(self) -> WeatherProvider:
        if self._weather_provider is None:
            self._weather_provider = get_weather_provider()
        return self._weather_provider

    @property
    def maps_provider(self) -> MapsProvider:
        if self._maps_provider is None:
            self._maps_provider = get_maps_provider()
        return self._maps_provider

    def get_weather(self, location: str, days: int = 5) -> Dict[str, Any]:
        try:
            return self.weather_provider.get_forecast(location, days)
        except ProviderError as exc:
            raise MCPError("Weather tool is temporarily unavailable", code="external") from exc

    def search_places(self, query: str, location: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        try:
            return self.maps_provider.search_places(query, location, limit)
        except ProviderError as exc:
            raise MCPError("Maps tool is temporarily unavailable", code="external") from exc

    def add_calendar_event(
        self,
        title: str,
        date: str,
        destination: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.calendar.add(title=title, date=date, destination=destination, notes=notes)

    def list_calendar_events(self, destination: Optional[str] = None) -> Dict[str, Any]:
        events = self.calendar.list_events(destination)
        return {"events": events, "count": len(events)}
