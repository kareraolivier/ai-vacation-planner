from typing import Dict, Optional


class PromptBuilder:
    """Build system and user prompts for itinerary generation"""

    @staticmethod
    def system_prompt() -> str:
        return """
You are an expert travel planner AI.

RULES:
1. Respond with valid JSON only.
2. Format:
{
  "days": [
    {
      "day": 1,
      "activities": ["activity1", "activity2"]
    }
  ]
}
3. Include real places.
4. Respect the budget.
5. Each day should contain 3-5 activities.
"""

    @staticmethod
    def user_prompt(
        destination: str,
        days: int,
        budget: float,
        travel_style: str,
        user_request: Optional[str] = None,
        tool_context: Optional[str] = None,
    ) -> str:

        budget_guidelines = PromptBuilder._get_budget_guidelines(
            travel_style
        )
        extra = ""
        if user_request:
            extra += f"\nTRAVELER REQUEST:\n{user_request}\n"
        if tool_context:
            extra += (
                "\nLIVE CONTEXT FROM TOOLS:\n"
                f"{tool_context}\n"
                "Use this information when it is relevant. "
                "If weather looks poor, prefer indoor or flexible activities. "
                "If a tool failed, continue with a useful plan.\n"
            )

        return f"""
Create a {days}-day itinerary for {destination}.

TRIP DETAILS:
- Destination: {destination}
- Duration: {days} days
- Budget: ${budget:.2f}
- Style: {travel_style}
{extra}
BUDGET GUIDELINES:
{budget_guidelines}

REQUIREMENTS:
1. Create exactly {days} days.
2. Each day must have 3-5 activities.
3. Include estimated costs when relevant.
4. Stay within budget.
5. Use real locations.

Return ONLY valid JSON.
"""

    @staticmethod
    def _get_budget_guidelines(travel_style: str) -> str:
        guidelines: Dict[str, str] = {
            "budget": (
                "Focus on affordable attractions and local transport."
            ),
            "luxury": (
                "Premium experiences and fine dining."
            ),
            "family": (
                "Family-friendly attractions and relaxed pacing."
            ),
            "adventure": (
                "Outdoor activities and unique experiences."
            )
        }

        return guidelines.get(
            travel_style.lower(),
            guidelines["budget"]
        )
