import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from ...core.config import settings
from ...schemas.planning import GeneratedItinerary
from ..tools.base import AgentTool
from .state import PlanningState

logger = logging.getLogger(__name__)

REASON_SYSTEM_PROMPT = """You are a vacation planning agent.
Decide which tools, if any, are needed to answer the traveler. Call only the tools that add useful information.
Available capabilities include weather, maps/places, pricing, and the travel knowledge base.
Do not call a tool unless the request needs it. After you have enough information, stop calling tools.
Do not write the final day-by-day itinerary yourself; another step will compose it.
"""

COMPOSE_SYSTEM_PROMPT = """You are a vacation planner. Create a practical day-by-day itinerary.
Use the traveler request, trip constraints, and any tool results provided.
If a tool failed, continue with a useful plan and mention the gap in notes.
Prefer indoor or flexible activities when weather looks poor.
Keep each day's activities as concise strings that a traveler can follow.
"""


class PlanningGraph:
    def __init__(
        self,
        model,
        tools: List[AgentTool],
        max_iterations: Optional[int] = None,
    ):
        self.model = model
        self.tools = {tool.name: tool for tool in tools}
        self.langchain_tools = [tool.as_langchain_tool() for tool in tools]
        self.max_iterations = max_iterations or settings.AGENT_MAX_TOOL_ITERATIONS
        self._model_with_tools = self.model.bind_tools(self.langchain_tools) if self.langchain_tools else self.model
        self.app = self._build()

    def _build(self):
        graph = StateGraph(PlanningState)
        graph.add_node("reason", self.reason)
        graph.add_node("tools", self.execute_tools)
        graph.add_node("compose", self.compose)
        graph.add_edge(START, "reason")
        graph.add_conditional_edges("reason", self.route_after_reason, {
            "tools": "tools",
            "compose": "compose",
        })
        graph.add_edge("tools", "reason")
        graph.add_edge("compose", END)
        return graph.compile()

    def reason(self, state: PlanningState) -> Dict[str, Any]:
        messages = list(state.get("messages") or [])
        outgoing = []
        if not messages:
            outgoing = [
                SystemMessage(content=REASON_SYSTEM_PROMPT),
                HumanMessage(content=self._reason_user_prompt(state)),
            ]
            messages = outgoing
        response = self._model_with_tools.invoke(messages)
        outgoing.append(response)
        return {
            "messages": outgoing,
            "iteration": int(state.get("iteration") or 0) + 1,
        }

    def route_after_reason(self, state: PlanningState) -> str:
        if int(state.get("iteration") or 0) >= self.max_iterations:
            return "compose"
        last = (state.get("messages") or [None])[-1]
        tool_calls = getattr(last, "tool_calls", None) if last is not None else None
        if tool_calls:
            return "tools"
        return "compose"

    def execute_tools(self, state: PlanningState) -> Dict[str, Any]:
        last = (state.get("messages") or [None])[-1]
        tool_calls = getattr(last, "tool_calls", None) or []
        messages = []
        tool_results = list(state.get("tool_results") or [])
        tools_used = list(state.get("tools_used") or [])
        warnings = list(state.get("warnings") or [])

        for call in tool_calls:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
            args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
            call_id = call.get("id") if isinstance(call, dict) else getattr(call, "id", name)
            tool = self.tools.get(name)
            if tool is None:
                content = json.dumps({"success": False, "error": f"Unknown tool: {name}"})
                warnings.append(f"Unknown tool requested: {name}")
            else:
                content = tool.run(**(args or {}))
                if name not in tools_used:
                    tools_used.append(name)
                parsed = _parse_tool_payload(content)
                tool_results.append({"tool": name, "result": parsed})
                if not parsed.get("success"):
                    warnings.append(f"{name} failed: {parsed.get('error') or 'unknown error'}")
            messages.append(ToolMessage(content=content, tool_call_id=call_id))

        return {
            "messages": messages,
            "tool_results": tool_results,
            "tools_used": tools_used,
            "warnings": warnings,
        }

    def compose(self, state: PlanningState) -> Dict[str, Any]:
        prompt = self._compose_prompt(state)
        messages = [
            SystemMessage(content=COMPOSE_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        itinerary = self._generate_itinerary(messages, state)
        return {
            "summary": itinerary.summary,
            "itinerary": [day.model_dump() for day in itinerary.days],
            "warnings": list(state.get("warnings") or []) + itinerary.notes,
        }

    def invoke(self, state: PlanningState) -> PlanningState:
        return self.app.invoke(state)

    def _reason_user_prompt(self, state: PlanningState) -> str:
        parts = [
            f"Traveler request: {state.get('user_request')}",
            f"Destination: {state.get('destination') or 'unknown'}",
            f"Days: {state.get('days')}",
        ]
        if state.get("budget") is not None:
            parts.append(f"Budget: {state.get('budget')}")
        if state.get("trip_style"):
            parts.append(f"Trip style: {state.get('trip_style')}")
        return "\n".join(parts)

    def _compose_prompt(self, state: PlanningState) -> str:
        return (
            f"Traveler request: {state.get('user_request')}\n"
            f"Destination: {state.get('destination') or 'unknown'}\n"
            f"Days: {state.get('days')}\n"
            f"Budget: {state.get('budget')}\n"
            f"Trip style: {state.get('trip_style')}\n"
            f"Tool results: {json.dumps(state.get('tool_results') or [], default=str)}\n"
            f"Warnings: {json.dumps(state.get('warnings') or [])}\n"
            "Return a complete itinerary covering every requested day."
        )

    def _generate_itinerary(self, messages: List, state: PlanningState) -> GeneratedItinerary:
        try:
            structured = self.model.with_structured_output(GeneratedItinerary)
            result = structured.invoke(messages)
            if isinstance(result, GeneratedItinerary):
                return result
            if isinstance(result, dict):
                return GeneratedItinerary.model_validate(result)
        except Exception as exc:
            logger.warning("Structured itinerary generation failed, falling back to JSON parse: %s", exc)

        raw = self.model.invoke(messages)
        content = getattr(raw, "content", None) or str(raw)
        parsed = _extract_json(content)
        if parsed:
            try:
                return GeneratedItinerary.model_validate(parsed)
            except Exception:
                pass

        days = int(state.get("days") or 1)
        destination = state.get("destination") or "the destination"
        return GeneratedItinerary(
            summary=f"A {days}-day plan for {destination}. Some live details were unavailable.",
            days=[
                {"day": index, "activities": [f"Explore {destination} — refine after live data is available"]}
                for index in range(1, days + 1)
            ],
            notes=["The model did not return a structured itinerary; a fallback plan was generated."],
        )


def _parse_tool_payload(content: str) -> Dict[str, Any]:
    try:
        payload = json.loads(content)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    return {"success": False, "error": content}


def _extract_json(content: str) -> Optional[dict]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                payload = json.loads(text[start:end + 1])
                return payload if isinstance(payload, dict) else None
            except json.JSONDecodeError:
                return None
        return None


def build_planning_graph(model, tools: List[AgentTool], max_iterations: Optional[int] = None) -> PlanningGraph:
    return PlanningGraph(model=model, tools=tools, max_iterations=max_iterations)
