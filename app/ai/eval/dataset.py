import json
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "data" / "eval" / "golden_itineraries.json"


def load_golden_dataset(path: Path = DEFAULT_DATASET) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("Golden dataset must be a JSON list")
    return payload
