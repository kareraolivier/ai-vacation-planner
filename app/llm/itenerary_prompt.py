from typing import Dict


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
        travel_style: str
    ) -> str:

        budget_guidelines = PromptBuilder._get_budget_guidelines(
            travel_style
        )

        return f"""
Create a {days}-day itinerary for {destination}.

TRIP DETAILS:
- Destination: {destination}
- Duration: {days} days
- Budget: ${budget:.2f}
- Style: {travel_style}

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
