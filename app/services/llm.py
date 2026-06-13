import json
import anthropic
from typing import List, Dict, Any, Optional
from app.core.config import settings


class LLMService:
    def __init__(self):
        """Initialize with Claude Haiku 4.5"""
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment variables")

        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-haiku-4-5"

    def generate_itinerary(
        self,
        destination: str,
        days: int,
        budget: float,
        travel_style: str
    ) -> List[Dict[str, Any]]:
        """Generate itinerary"""

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            destination, days, budget, travel_style
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            itinerary_text = response.content[0].text

            # Extract JSON
            itinerary_text = self._extract_json(itinerary_text)
            itinerary_data = json.loads(itinerary_text)

            return self._format_itinerary(itinerary_data, days, destination)

        except Exception as e:
            print(f"Claude API error: {e}")
            return self._get_fallback_itinerary(destination, days)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response"""
        text = text.strip()

        # Remove markdown code blocks
        if '```json' in text:
            text = text.split('```json')[1]
        if '```' in text:
            text = text.split('```')[0]
        if text.endswith('```'):
            text = text[:-3]

        # Find JSON object
        start = text.find('{')
        end = text.rfind('}') + 1

        if start != -1 and end != 0:
            text = text[start:end]

        return text.strip()

    def _build_system_prompt(self) -> str:
        """Build system prompt"""
        return """You are an expert travel planner AI. Create detailed, realistic travel itineraries.

RULES:
1. Respond with valid JSON only
2. Format: {"days": [{"day": 1, "activities": ["activity1", "activity2"]}]}
3. Include specific, real places
4. Respect budget constraints
5. Each day: 3-5 activities

Example: {"days": [{"day": 1, "activities": ["Morning: Eiffel Tower", "Afternoon: Louvre Museum"]}]}"""

    def _build_user_prompt(self, destination: str, days: int, budget: float, travel_style: str) -> str:
        """Build user prompt"""
        return f"""Create a {days}-day itinerary for {destination}.

Details:
- Destination: {destination}
- Days: {days}
- Budget: ${budget}
- Style: {travel_style}

Return ONLY valid JSON with format: {{"days": [{{"day": 1, "activities": []}}]}}"""

    def _format_itinerary(self, data: dict, expected_days: int, destination: str) -> List[dict]:
        """Format itinerary"""
        if "days" not in data:
            return self._get_fallback_itinerary(destination, expected_days)

        return data["days"][:expected_days]

    def _get_fallback_itinerary(self, destination: str, days: int) -> List[dict]:
        """Fallback itinerary"""
        return [{"day": i, "activities": [f"Explore {destination}"]} for i in range(1, days + 1)]
