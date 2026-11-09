from typing import List, Dict, Any, Optional

import anthropic

from app.core.config import settings
from app.ai.guardrails.errors import GuardrailError
from app.ai.llm.itenerary_prompt import PromptBuilder
from app.ai.llm.response_parser import (
    ResponseParser,
    FallbackItinerary
)
from app.ai.observability import extract_usage, record_llm_usage


class LLMService:
    """Claude itinerary generator used by both direct AI generation and the agent compose step."""

    def __init__(self):

        if not settings.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not found"
            )

        self.client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY
        )

        self.model = settings.LLM_MODEL
        self.prompt_builder = PromptBuilder()
        self.parser = ResponseParser()
        self.fallback = FallbackItinerary()

    def generate_itinerary(
        self,
        destination: str,
        days: int,
        budget: float,
        travel_style: str,
        user_request: Optional[str] = None,
        tool_context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                system=self.prompt_builder.system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": self.prompt_builder.user_prompt(
                            destination=destination,
                            days=days,
                            budget=budget,
                            travel_style=travel_style,
                            user_request=user_request,
                            tool_context=tool_context,
                        )
                    }
                ]
            )
            usage = extract_usage(response)
            record_llm_usage(
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                model=self.model,
            )
            response_text = response.content[0].text
            return self.parser.parse_itinerary_response(
                response_text=response_text,
                expected_days=days
            )

        except ValueError as exc:
            if settings.GUARDRAILS_REJECT_INVALID:
                raise GuardrailError(str(exc), code="invalid_output") from exc
            return self.fallback.create(
                destination=destination,
                days=days
            )

        except Exception as e:
            print(f"Claude error: {e}")

            return self.fallback.create(
                destination=destination,
                days=days
            )
