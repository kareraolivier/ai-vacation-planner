from typing import Any, Dict, Optional

from ...core.config import settings
from .base import HttpProviderClient, ProviderError, WeatherProvider


class OpenMeteoWeatherProvider(WeatherProvider):
    def __init__(
        self,
        api_url: Optional[str] = None,
        geocode_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_url = (api_url or settings.WEATHER_API_URL).rstrip("/")
        self.geocode_url = (geocode_url or settings.WEATHER_GEOCODE_URL).rstrip("/")
        self.api_key = api_key or settings.WEATHER_API_KEY
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self.client = HttpProviderClient(timeout=timeout or settings.WEATHER_TIMEOUT, headers=headers)

    def get_forecast(self, location: str, days: int) -> Dict[str, Any]:
        geo = self.client.get(
            f"{self.geocode_url}/search",
            params={"name": location, "count": 1, "language": "en", "format": "json"},
        )
        results = geo.get("results") if isinstance(geo, dict) else None
        if not results:
            raise ProviderError("weather", f"Could not geocode location: {location}")

        place = results[0]
        forecast = self.client.get(
            f"{self.api_url}/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "forecast_days": max(1, min(days, 16)),
                "timezone": "auto",
            },
        )
        daily = forecast.get("daily") or {}
        days_out = []
        times = daily.get("time") or []
        for index, date in enumerate(times):
            days_out.append({
                "date": date,
                "weather_code": _at(daily.get("weather_code"), index),
                "temperature_max_c": _at(daily.get("temperature_2m_max"), index),
                "temperature_min_c": _at(daily.get("temperature_2m_min"), index),
                "precipitation_mm": _at(daily.get("precipitation_sum"), index),
            })

        return {
            "location": place.get("name") or location,
            "country": place.get("country"),
            "latitude": place.get("latitude"),
            "longitude": place.get("longitude"),
            "days": days_out,
            "provider": "openmeteo",
        }


def _at(values, index):
    if not values or index >= len(values):
        return None
    return values[index]


def get_weather_provider() -> WeatherProvider:
    provider = (settings.WEATHER_PROVIDER or "openmeteo").lower()
    if provider == "openmeteo":
        return OpenMeteoWeatherProvider()
    raise ProviderError("weather", f"Unsupported weather provider: {settings.WEATHER_PROVIDER}")
