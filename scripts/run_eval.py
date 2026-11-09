"""Evaluate the golden itinerary dataset with the same heuristic metrics used in production."""

import json
import sys
from pathlib import Path

import os

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./vacation_planner.db")
os.environ.setdefault("SECRET_KEY", "eval-script")

from app.ai.eval.dataset import load_golden_dataset
from app.ai.eval.evaluator import evaluate_itinerary


def main() -> None:
    cases = load_golden_dataset()
    rows = []
    for case in cases:
        itinerary = case.get("actual_output")
        if isinstance(itinerary, dict):
            itinerary = itinerary.get("days") or itinerary.get("itinerary") or []
        if not isinstance(itinerary, list):
            itinerary = []
        result = evaluate_itinerary(
            user_request=case["input"],
            destination=case.get("destination") or "",
            expected_days=int(case.get("days") or 1),
            itinerary=itinerary,
        )
        passed = result["passed"]
        expected = bool(case.get("expect_pass", True))
        rows.append(
            {
                "id": case["id"],
                "overall": result["overall_score"],
                "passed": passed,
                "expect_pass": expected,
                "ok": passed == expected,
                "scores": result["scores"],
            }
        )
    print(json.dumps(rows, indent=2))
    failures = [row for row in rows if not row["ok"]]
    if failures:
        raise SystemExit(f"{len(failures)} golden cases did not match expect_pass")
    print(f"\n{len(rows)} golden cases matched expectations.")


if __name__ == "__main__":
    main()
