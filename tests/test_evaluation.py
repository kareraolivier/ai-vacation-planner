import pytest

from app.ai.eval.dataset import load_golden_dataset
from app.ai.eval.evaluator import evaluate_itinerary
from app.ai.llm.response_parser import ResponseParser


def test_golden_dataset_matches_expected_pass_fail():
    for case in load_golden_dataset():
        itinerary = case["actual_output"]
        if isinstance(itinerary, dict):
            itinerary = itinerary.get("days") or []
        if not isinstance(itinerary, list):
            itinerary = []
        result = evaluate_itinerary(
            user_request=case["input"],
            destination=case.get("destination") or "",
            expected_days=int(case.get("days") or 1),
            itinerary=itinerary,
        )
        assert result["passed"] is case["expect_pass"], case["id"]


def test_relevant_complete_valid_paris_plan():
    itinerary = [
        {"day": 1, "activities": ["Louvre", "Tuileries", "Latin Quarter"]},
        {"day": 2, "activities": ["Musee d'Orsay", "Covered passages", "Dinner in Paris"]},
    ]
    result = evaluate_itinerary(
        "Plan my Paris trip and include museum time.",
        "Paris",
        2,
        itinerary,
    )
    assert result["follows_format"] is True
    assert result["complete"] is True
    assert result["relevant"] is True
    assert result["valid"] is True
    assert result["passed"] is True


def test_incomplete_itinerary_fails_completeness():
    result = evaluate_itinerary(
        "Plan 4 days in Tokyo",
        "Tokyo",
        4,
        [{"day": 1, "activities": ["Senso-ji"]}],
    )
    assert result["complete"] is False
    assert result["passed"] is False


def test_parser_rejects_non_json_and_missing_days():
    parser = ResponseParser()
    with pytest.raises(ValueError):
        parser.parse_itinerary_response("not json", expected_days=2)
    with pytest.raises(ValueError):
        parser.parse_itinerary_response('{"itinerary": []}', expected_days=2)


def test_parser_accepts_fenced_json():
    parser = ResponseParser()
    days = parser.parse_itinerary_response(
        '```json\n{"days": [{"day": 1, "activities": ["Cafe"]}, {"day": 2, "activities": ["Castle"]}]}\n```',
        expected_days=2,
    )
    assert len(days) == 2
