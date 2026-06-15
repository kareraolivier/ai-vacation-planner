from typing import List, Dict, Any

import anthropic

from app.core.config import settings
from app.llm.itenerary_prompt import PromptBuilder
from app.llm.response_parser import (
    ResponseParser,
    FallbackItinerary
)


class LLMService:
    """Claude itinerary generator"""

    def __init__(self):

        if not settings.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not found"
            )

        self.client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY
        )

        self.model = "claude-haiku-4-5"

        self.prompt_builder = PromptBuilder()
        self.parser = ResponseParser()
        self.fallback = FallbackItinerary()

    def generate_itinerary(
        self,
        destination: str,
        days: int,
        budget: float,
        travel_style: str
    ) -> List[Dict[str, Any]]:

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                system=self.prompt_builder.system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": self.prompt_builder.user_prompt(
                            destination=destination,
                            days=days,
                            budget=budget,
                            travel_style=travel_style
                        )
                    }
                ]
            )

            response_text = response.content[0].text

            return self.parser.parse_itinerary_response(
                response_text=response_text,
                expected_days=days
            )

        except Exception as e:
            print(f"Claude error: {e}")

            return self.fallback.create(
                destination=destination,
                days=days
            )
