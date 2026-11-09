from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4


class TravelCalendarStore:
    """In-process trip calendar used by the MCP calendar tools."""

    def __init__(self):
        self._events: List[Dict[str, Optional[str]]] = []
        self._lock = Lock()

    def add(
        self,
        title: str,
        date: str,
        destination: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
        event = {
            "id": str(uuid4()),
            "title": title,
            "date": date,
            "destination": destination,
            "notes": notes,
        }
        with self._lock:
            self._events.append(event)
        return event

    def list_events(self, destination: Optional[str] = None) -> List[Dict[str, Optional[str]]]:
        with self._lock:
            events = list(self._events)
        if destination:
            wanted = destination.lower()
            events = [event for event in events if (event.get("destination") or "").lower() == wanted]
        return events

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


travel_calendar = TravelCalendarStore()
