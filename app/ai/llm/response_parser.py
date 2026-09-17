import json
from typing import Dict, Any, List


class ResponseParser:
    """Parse Claude responses and extract itinerary JSON"""

    @staticmethod
    def extract_json(text: str) -> str:
        text = text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "", 1)

        if text.startswith("```"):
            text = text.replace("```", "", 1)

        if text.endswith("```"):
            text = text[:-3]

        start = text.find("{")
        end = text.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")

        return text[start:end].strip()

    @staticmethod
    def parse_itinerary_response(
        response_text: str,
        expected_days: int
    ) -> List[Dict[str, Any]]:

        json_text = ResponseParser.extract_json(response_text)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON returned by Claude: {str(e)}"
            )

        return ResponseParser._format_days(
            data,
            expected_days
        )

    @staticmethod
    def _format_days(
        data: Dict[str, Any],
        expected_days: int
    ) -> List[Dict[str, Any]]:

        if "days" not in data:
            raise ValueError(
                "Response does not contain a 'days' field"
            )

        days_list = data["days"]

        if not isinstance(days_list, list):
            raise ValueError("'days' must be a list")

        if len(days_list) < expected_days:
            days_list = ResponseParser._adjust_day_count(
                days_list,
                expected_days
            )

        return days_list[:expected_days]

    @staticmethod
    def _adjust_day_count(
        days_list: List[Dict[str, Any]],
        expected_days: int
    ) -> List[Dict[str, Any]]:

        current_length = len(days_list)

        for day in range(current_length + 1, expected_days + 1):
            days_list.append(
                {
                    "day": day,
                    "activities": [
                        f"Explore local attractions on day {day}"
                    ]
                }
            )

        return days_list


class FallbackItinerary:

    @staticmethod
    def create(
        destination: str,
        days: int
    ) -> List[Dict[str, Any]]:

        return [
            {
                "day": day,
                "activities": [
                    f"Morning: Explore {destination}",
                    f"Afternoon: Visit attractions in {destination}",
                    f"Evening: Enjoy local cuisine"
                ]
            }
            for day in range(1, days + 1)
        ]
