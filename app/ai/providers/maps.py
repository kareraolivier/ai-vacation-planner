from typing import Any, Dict, Optional

from ...core.config import settings
from .base import HttpProviderClient, ProviderError, MapsProvider


class NominatimMapsProvider(MapsProvider):
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_url = (api_url or settings.MAPS_API_URL).rstrip("/")
        headers = {"User-Agent": user_agent or settings.MAPS_USER_AGENT, "Accept": "application/json"}
        api_key = api_key or settings.MAPS_API_KEY
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.client = HttpProviderClient(timeout=timeout or settings.MAPS_TIMEOUT, headers=headers)

    def search_places(self, query: str, location: Optional[str], limit: int) -> Dict[str, Any]:
        search_query = f"{query} {location}".strip() if location else query
        payload = self.client.get(
            f"{self.api_url}/search",
            params={
                "q": search_query,
                "format": "json",
                "limit": max(1, min(limit, 10)),
                "addressdetails": 1,
            },
        )
        if not isinstance(payload, list):
            raise ProviderError("maps", "Unexpected maps provider response")

        places = []
        for item in payload:
            places.append({
                "name": item.get("display_name"),
                "lat": item.get("lat"),
                "lon": item.get("lon"),
                "type": item.get("type"),
                "category": item.get("class"),
            })
        return {
            "query": search_query,
            "places": places,
            "provider": "nominatim",
        }


def get_maps_provider() -> MapsProvider:
    provider = (settings.MAPS_PROVIDER or "nominatim").lower()
    if provider == "nominatim":
        return NominatimMapsProvider()
    raise ProviderError("maps", f"Unsupported maps provider: {settings.MAPS_PROVIDER}")
