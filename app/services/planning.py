from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..core.config import settings
from ..schemas.itinerary import DayActivity, ItineraryCreate
from ..schemas.planning import PlanningRequest
from ..ai.agents.graph import PlanningGraph, build_planning_graph
from ..ai.agents.state import PlanningState
from ..ai.eval.evaluator import evaluate_itinerary
from ..ai.guardrails.errors import GuardrailError
from ..ai.guardrails.policy import check_input_guardrails, check_output_guardrails
from ..ai.llm.itinerary_generator import LLMService
from ..ai.observability import trace_span
from .itinerary import ItineraryService
from ..ai.providers.llm import LLMConfigurationError, get_chat_model
from ..ai.tools.registry import ToolRegistry
from .knowledge import KnowledgeService
from .trip import TripService


class PlanningService:
    def __init__(
        self,
        db: Session,
        knowledge_service: Optional[KnowledgeService] = None,
        graph: Optional[PlanningGraph] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.db = db
        self.trip_service = TripService(db)
        self.itinerary_service = ItineraryService(db)
        self.knowledge_service = knowledge_service or KnowledgeService(db)
        self.tool_registry = tool_registry or ToolRegistry(self.knowledge_service)
        self.graph = graph

    def plan_trip(self, user_id: UUID, request: PlanningRequest) -> dict:
        destination = request.destination.title() if request.destination else None
        days = request.days
        budget = request.budget
        trip_style = request.trip_style
        trip_id = request.trip_id

        if trip_id:
            trip = self.trip_service.get_user_trip(user_id, trip_id)
            if not trip:
                raise ValueError("Trip not found")
            destination = destination or trip.destination
            days = days or trip.days
            budget = budget if budget is not None else trip.budget
            trip_style = trip_style or trip.trip_style

        if not destination:
            destination = _infer_destination(request.message) or "Unknown"
        if not days:
            days = 3

        with trace_span("plan_trip", model=settings.LLM_MODEL, destination=destination) as span:
            try:
                check_input_guardrails(request.message)
                graph = self.graph or self._build_graph()
                initial: PlanningState = {
                    "messages": [],
                    "user_request": request.message,
                    "destination": destination,
                    "days": days,
                    "budget": budget,
                    "trip_style": trip_style,
                    "tool_results": [],
                    "tools_used": [],
                    "warnings": [],
                    "iteration": 0,
                    "summary": "",
                    "itinerary": [],
                }
                result = graph.invoke(initial)
                itinerary = check_output_guardrails(
                    result.get("itinerary") or [],
                    destination=destination,
                    expected_days=int(days),
                )
                warnings = list(result.get("warnings") or [])
                if getattr(self.tool_registry, "mcp_warning", None):
                    warnings.append(self.tool_registry.mcp_warning)

                evaluation = None
                if settings.EVALUATION_ENABLED:
                    evaluation = evaluate_itinerary(
                        user_request=request.message,
                        destination=destination,
                        expected_days=int(days),
                        itinerary=itinerary,
                    )

                persisted_trip_id = None
                message = "Trip plan generated successfully"
                if request.persist_itinerary and trip_id:
                    days_models = [
                        DayActivity(day=item.get("day", index + 1), activities=item.get("activities") or ["Free time"])
                        for index, item in enumerate(itinerary)
                    ] or [DayActivity(day=1, activities=["Explore the destination"])]
                    saved = self.itinerary_service.create_itinerary(
                        user_id,
                        ItineraryCreate(trip_id=trip_id, days=days_models),
                    )
                    if saved:
                        persisted_trip_id = saved["trip_id"]
                        itinerary = saved["itinerary"]
                        message = "Trip plan generated and itinerary saved"

                return {
                    "trip_id": persisted_trip_id or trip_id,
                    "destination": result.get("destination") or destination,
                    "summary": result.get("summary") or "",
                    "itinerary": itinerary,
                    "tools_used": result.get("tools_used") or [],
                    "warnings": warnings,
                    "message": message,
                    "evaluation": evaluation,
                    "observability": span.snapshot(),
                }
            except GuardrailError:
                span.metadata["blocked"] = True
                raise


    def _build_graph(self) -> PlanningGraph:
        try:
            model = get_chat_model()
            llm_service = LLMService()
        except (LLMConfigurationError, ValueError) as exc:
            raise RuntimeError(str(exc)) from exc
        return build_planning_graph(model, self.tool_registry.all(), llm_service=llm_service)


def _infer_destination(message: str) -> Optional[str]:
    text = message.strip()
    lowered = text.lower()
    marker = " trip"
    if "my " in lowered and marker in lowered:
        start = lowered.find("my ") + 3
        end = lowered.find(marker, start)
        if end > start:
            return text[start:end].strip().title()
    return None
