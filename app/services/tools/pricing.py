from typing import Optional

from pydantic import BaseModel, Field

from ..providers.base import PricingProvider
from ..providers.pricing import get_pricing_provider
from .base import AgentTool, ToolResult


class PricingToolInput(BaseModel):
    destination: str = Field(..., min_length=1, max_length=120, description="Destination to price")
    days: int = Field(..., ge=1, le=365, description="Trip length in days")
    budget: Optional[float] = Field(None, gt=0, description="Traveler budget if known")
    trip_style: Optional[str] = Field(None, description="budget, luxury, family, or adventure")
    travelers: int = Field(1, ge=1, le=20, description="Number of travelers")


class PricingTool(AgentTool):
    name = "estimate_pricing"
    description = (
        "Estimate trip costs for a destination and travel style. "
        "Use when the traveler mentions budget, prices, or affordability."
    )
    args_schema = PricingToolInput

    def __init__(self, provider: PricingProvider = None):
        self.provider = provider or get_pricing_provider()

    def execute(self, params: PricingToolInput) -> ToolResult:
        data = self.provider.estimate(
            destination=params.destination,
            days=params.days,
            budget=params.budget,
            trip_style=params.trip_style,
            travelers=params.travelers,
        )
        return ToolResult(success=True, data=data)
