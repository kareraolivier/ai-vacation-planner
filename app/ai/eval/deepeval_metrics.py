"""DeepEval-style metrics for itinerary quality.

Measures are heuristic so CI does not need a live LLM judge. The classes follow
DeepEval's BaseMetric / LLMTestCase shape. On Python 3.10+ you can swap in the
real DeepEval base classes; the 3.9 test venv cannot import current DeepEval.
"""

from typing import List, Optional

from .metrics import completeness_score, format_score, relevance_score, validity_score


class BaseMetric:
    threshold: float
    score: Optional[float]
    reason: Optional[str]
    success: Optional[bool]

    def is_successful(self) -> bool:
        return bool(self.success)


class LLMTestCase:
    def __init__(
        self,
        input: str,
        actual_output: str,
        expected_output: Optional[str] = None,
        context: Optional[List[str]] = None,
    ):
        self.input = input
        self.actual_output = actual_output
        self.expected_output = expected_output
        self.context = context or []


def _days_from_case(test_case: LLMTestCase) -> int:
    for item in test_case.context or []:
        if isinstance(item, str) and item.startswith("days="):
            try:
                return int(item.split("=", 1)[1])
            except ValueError:
                return 1
    return 1


def _destination_from_case(test_case: LLMTestCase) -> str:
    for item in test_case.context or []:
        if isinstance(item, str) and item.startswith("destination="):
            return item.split("=", 1)[1]
    return ""


class ItineraryFormatMetric(BaseMetric):
    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
        self.score = None
        self.reason = ""
        self.success = None

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        result = format_score(test_case.actual_output)
        self.score = result["score"]
        self.reason = result["reason"]
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    @property
    def __name__(self) -> str:
        return "Itinerary Format"


class ItineraryCompletenessMetric(BaseMetric):
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self.score = None
        self.reason = ""
        self.success = None

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        result = completeness_score(test_case.actual_output, _days_from_case(test_case))
        self.score = result["score"]
        self.reason = result["reason"]
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    @property
    def __name__(self) -> str:
        return "Itinerary Completeness"


class ItineraryRelevanceMetric(BaseMetric):
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self.score = None
        self.reason = ""
        self.success = None

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        result = relevance_score(
            test_case.actual_output,
            _destination_from_case(test_case),
            test_case.input,
        )
        self.score = result["score"]
        self.reason = result["reason"]
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    @property
    def __name__(self) -> str:
        return "Itinerary Relevance"


class ItineraryValidityMetric(BaseMetric):
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self.score = None
        self.reason = ""
        self.success = None

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        result = validity_score(test_case.actual_output, _days_from_case(test_case))
        self.score = result["score"]
        self.reason = result["reason"]
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    @property
    def __name__(self) -> str:
        return "Itinerary Validity"
