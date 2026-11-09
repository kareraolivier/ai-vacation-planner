from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph.message import add_messages


class PlanningState(TypedDict):
    messages: Annotated[list, add_messages]
    user_request: str
    destination: str
    days: int
    budget: Optional[float]
    trip_style: Optional[str]
    tool_results: List[Dict[str, Any]]
    tools_used: List[str]
    warnings: List[str]
    iteration: int
    summary: str
    itinerary: List[Dict[str, Any]]
