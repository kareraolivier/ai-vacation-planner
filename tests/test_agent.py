from uuid import uuid4

from langchain_core.messages import AIMessage

from app.schemas.planning import PlanningRequest
from app.services.agents.graph import PlanningGraph
from app.services.planning import PlanningService
from app.services.tools.weather import WeatherTool
from app.services.tools.knowledge import KnowledgeTool
from app.services.rag.interfaces import RetrievedChunk


class ScriptedModel:
    def __init__(self, responses):
        self.responses = list(responses)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if self.responses:
            return self.responses.pop(0)
        return AIMessage(content="")


class FakeLLMService:
    def __init__(self, days=None):
        self.days = days or [{"day": 1, "activities": ["Musee d'Orsay", "Galerie Vivienne"]}]
        self.calls = []

    def generate_itinerary(self, destination, days, budget, travel_style, user_request=None, tool_context=None):
        self.calls.append({
            "destination": destination,
            "user_request": user_request,
            "tool_context": tool_context,
        })
        return self.days


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
    llm = FakeLLMService()
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
    )
    graph = PlanningGraph(
        model=model,
        tools=[
            WeatherTool(provider=FakeWeather()),
            KnowledgeTool(FakeKnowledgeService()),
        ],
        llm_service=llm,
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
    assert llm.calls
    assert "get_weather" in (llm.calls[0]["tool_context"] or "")
    assert result["iteration"] == 2


def test_agent_skips_tools_when_model_does_not_request_them():
    llm = FakeLLMService(days=[{"day": 1, "activities": ["Walk the Seine"]}])
    model = ScriptedModel(responses=[AIMessage(content="no tools needed")])
    graph = PlanningGraph(
        model=model,
        tools=[WeatherTool(provider=FakeWeather())],
        llm_service=llm,
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
    class BrokenWeather:
        def get_forecast(self, location, days):
            from app.services.providers.base import ProviderError
            raise ProviderError("weather", "weather API unavailable")

    llm = FakeLLMService(days=[{"day": 1, "activities": ["Indoor museum morning"]}])
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "get_weather", "args": {"location": "Paris", "days": 2}, "id": "w1"}],
            ),
            AIMessage(content="done"),
        ],
    )
    graph = PlanningGraph(
        model=model,
        tools=[WeatherTool(provider=BrokenWeather())],
        llm_service=llm,
        max_iterations=4,
    )
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


def test_planning_service_uses_existing_trip_and_can_skip_persist(db_session):
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

    graph = PlanningGraph(
        model=ScriptedModel(responses=[AIMessage(content="ok")]),
        tools=[],
        llm_service=FakeLLMService(days=[{"day": 1, "activities": ["Louvre"]}]),
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
