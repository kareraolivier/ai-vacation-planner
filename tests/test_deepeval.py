"""DeepEval tests over the golden itinerary dataset.

Custom metrics are heuristic so CI does not need a live LLM judge.
"""

import json

from app.ai.eval.dataset import load_golden_dataset
from app.ai.eval.deepeval_metrics import (
    ItineraryCompletenessMetric,
    ItineraryFormatMetric,
    ItineraryRelevanceMetric,
    ItineraryValidityMetric,
    LLMTestCase,
)


def _case(item: dict) -> LLMTestCase:
    output = item["actual_output"]
    if not isinstance(output, str):
        output = json.dumps(output)
    return LLMTestCase(
        input=item["input"],
        actual_output=output,
        context=[
            f"destination={item.get('destination') or ''}",
            f"days={item.get('days') or 1}",
        ],
    )


def test_deepeval_format_metric_on_golden_dataset():
    metric = ItineraryFormatMetric()
    for item in load_golden_dataset():
        metric.measure(_case(item))
        if item["id"] == "invalid-format":
            assert metric.is_successful() is False
        elif item["expect_pass"]:
            assert metric.is_successful() is True, item["id"]


def test_deepeval_completeness_and_relevance_on_good_cases():
    good = [item for item in load_golden_dataset() if item["expect_pass"]]
    for item in good:
        case = _case(item)
        completeness = ItineraryCompletenessMetric(threshold=0.6)
        relevance = ItineraryRelevanceMetric(threshold=0.5)
        validity = ItineraryValidityMetric(threshold=0.6)
        completeness.measure(case)
        relevance.measure(case)
        validity.measure(case)
        assert completeness.is_successful(), item["id"]
        assert relevance.is_successful(), item["id"]
        assert validity.is_successful(), item["id"]


def test_deepeval_flags_incomplete_and_wrong_destination():
    by_id = {item["id"]: item for item in load_golden_dataset()}
    incomplete = ItineraryCompletenessMetric(threshold=0.8)
    incomplete.measure(_case(by_id["incomplete-barcelona"]))
    assert incomplete.is_successful() is False

    relevance = ItineraryRelevanceMetric(threshold=0.6)
    relevance.measure(_case(by_id["wrong-destination"]))
    assert relevance.is_successful() is False
