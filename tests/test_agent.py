import json
from uuid import uuid4

from langchain_core.messages import AIMessage

from app.schemas.planning import GeneratedItinerary, PlanningRequest
from app.services.agents.graph import PlanningGraph
from app.services.planning import PlanningService
from app.services.tools.weather import WeatherTool
from app.services.tools.knowledge import KnowledgeTool
from app.services.rag.interfaces import RetrievedChunk


class ScriptedModel:
    def __init__(self, responses, structured=None):
        self.responses = list(responses)
        self.structured = structured
        self.invoke_calls = 0

    def bind_tools(self, tools):
        return self

    def with_structured_output(self, schema):
        return _Structured(self.structured)

    def invoke(self, messages):
        self.invoke_calls += 1
        if self.responses:
            return self.responses.pop(0)
        return AIMessage(content="")


class _Structured:
    def __init__(self, value):
        self.value = value

    def invoke(self, messages):
        return self.value


class FakeWeather:
    def get_forecast(self, location, days):
        return {"location": location, "days": [{"date": "2026-08-23", "precipitation_mm": 8}]}


class FakeKnowledgeService:
    def search(self, query, destination=None, top_k=5):
        return [
            RetrievedChunk(
                document_id=uuid4(),
                title="Paris Guide",
                source="paris.md",
                category="guide",
                destination="Paris",
                chunk_index=0,
                text="Covered passages are ideal on rainy days.",
                score=0.91,
            )
        ]


def test_agent_selects_needed_tools_and_then_composes():
    itinerary = GeneratedItinerary(
        summary="A weather-aware Paris weekend",
        days=[{"day": 1, "activities": ["Musee d'Orsay", "Galerie Vivienne"]}],
        notes=[],
    )
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "get_weather", "args": {"location": "Paris", "days": 3}, "id": "call-weather"},
                    {
                        "name": "search_travel_knowledge",
                        "args": {"query": "Paris rainy day activities", "destination": "Paris"},
                        "id": "call-rag",
                    },
                ],
            ),
            AIMessage(content="ready"),
        ],
        structured=itinerary,
    )
    graph = PlanningGraph(
        model=model,
        tools=[
            WeatherTool(provider=FakeWeather()),
            KnowledgeTool(FakeKnowledgeService()),
        ],
        max_iterations=4,
    )
    result = graph.invoke({
        "messages": [],
        "user_request": "Plan my Paris trip and include weather-friendly activities.",
        "destination": "Paris",
        "days": 3,
        "budget": 1500,
        "trip_style": "budget",
        "tool_results": [],
        "tools_used": [],
        "warnings": [],
        "iteration": 0,
        "summary": "",
        "itinerary": [],
    })

    assert set(result["tools_used"]) == {"get_weather", "search_travel_knowledge"}
    assert result["itinerary"][0]["activities"][0] == "Musee d'Orsay"
    assert result["summary"].startswith("A weather-aware")
    assert result["iteration"] == 2


def test_agent_skips_tools_when_model_does_not_request_them():
    itinerary = GeneratedItinerary(
        summary="Simple plan",
        days=[{"day": 1, "activities": ["Walk the Seine"]}],
    )
    model = ScriptedModel(responses=[AIMessage(content="no tools needed")], structured=itinerary)
    graph = PlanningGraph(
        model=model,
        tools=[WeatherTool(provider=FakeWeather())],
        max_iterations=3,
    )
    result = graph.invoke({
        "messages": [],
        "user_request": "Give me a one-day Paris outline",
        "destination": "Paris",
        "days": 1,
        "budget": None,
        "trip_style": None,
        "tool_results": [],
        "tools_used": [],
        "warnings": [],
        "iteration": 0,
        "summary": "",
        "itinerary": [],
    })
    assert result["tools_used"] == []
    assert result["itinerary"][0]["day"] == 1


def test_agent_continues_when_a_tool_fails():
    itinerary = GeneratedItinerary(
        summary="Plan without live weather",
        days=[{"day": 1, "activities": ["Indoor museum morning"]}],
        notes=["Weather data was unavailable."],
    )

    class BrokenWeather:
        def get_forecast(self, location, days):
            from app.services.providers.base import ProviderError
            raise ProviderError("weather", "weather API unavailable")

    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "get_weather", "args": {"location": "Paris", "days": 2}, "id": "w1"}],
            ),
            AIMessage(content="done"),
        ],
        structured=itinerary,
    )
    graph = PlanningGraph(model=model, tools=[WeatherTool(provider=BrokenWeather())], max_iterations=4)
    result = graph.invoke({
        "messages": [],
        "user_request": "Paris with weather-friendly ideas",
        "destination": "Paris",
        "days": 2,
        "budget": None,
        "trip_style": None,
        "tool_results": [],
        "tools_used": [],
        "warnings": [],
        "iteration": 0,
        "summary": "",
        "itinerary": [],
    })
    assert result["itinerary"]
    assert any("get_weather failed" in warning for warning in result["warnings"])


def test_planning_service_uses_existing_trip_and_can_skip_persist(db_session, monkeypatch):
    from app.repositories.user import UserRepository
    from app.services.trip import TripService
    from app.schemas.trip import TripCreate

    users = UserRepository(db_session)
    user = users.create(
        email="planner@example.com",
        username="planner",
        hashed_password="x",
        full_name="Planner",
    )
    trip = TripService(db_session).create_trip(
        user.id,
        TripCreate(destination="Paris", days=3, budget=1200, trip_style="budget"),
    )

    itinerary = GeneratedItinerary(
        summary="Saved plan",
        days=[{"day": 1, "activities": ["Louvre"]}],
    )
    graph = PlanningGraph(
        model=ScriptedModel(responses=[AIMessage(content="ok")], structured=itinerary),
        tools=[],
        max_iterations=2,
    )
    service = PlanningService(db_session, graph=graph)
    result = service.plan_trip(
        user.id,
        PlanningRequest(message="Plan my Paris trip", trip_id=trip["id"], persist_itinerary=False),
    )
    assert result["destination"] == "Paris"
    assert result["trip_id"] == trip["id"]
    assert result["message"] == "Trip plan generated successfully"
