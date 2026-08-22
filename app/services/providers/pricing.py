from typing import Any, Dict, Optional

from ...core.config import settings
from .base import HttpProviderClient, ProviderError, PricingProvider


class HttpPricingProvider(PricingProvider):
    """Calls a configured pricing API. No live prices are invented when the URL is unset."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_url = (api_url if api_url is not None else settings.PRICING_API_URL) or ""
        self.api_url = self.api_url.rstrip("/")
        headers = {"Accept": "application/json"}
        api_key = api_key or settings.PRICING_API_KEY
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.client = HttpProviderClient(timeout=timeout or settings.PRICING_TIMEOUT, headers=headers)

    def estimate(
        self,
        destination: str,
        days: int,
        budget: Optional[float],
        trip_style: Optional[str],
        travelers: int,
    ) -> Dict[str, Any]:
        if not self.api_url:
            raise ProviderError(
                "pricing",
                "Pricing provider is not configured. Set PRICING_API_URL to enable live estimates.",
            )

        return self.client.post(
            self.api_url,
            json={
                "destination": destination,
                "days": days,
                "budget": budget,
                "trip_style": trip_style,
                "travelers": travelers,
            },
        )


def get_pricing_provider() -> PricingProvider:
    provider = (settings.PRICING_PROVIDER or "http").lower()
    if provider == "http":
        return HttpPricingProvider()
    raise ProviderError("pricing", f"Unsupported pricing provider: {settings.PRICING_PROVIDER}")
