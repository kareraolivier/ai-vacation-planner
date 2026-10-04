import pytest
from langchain_core.messages import AIMessage

from app.ai.agents.graph import PlanningGraph
from app.ai.mcp.adapter import discover_mcp_tools
from app.ai.mcp.calendar import TravelCalendarStore
from app.ai.mcp.client import FakeMCPClient, InProcessMCPClient
from app.ai.mcp.errors import MCPError
from app.ai.mcp.handlers import TravelToolHandlers
from app.ai.mcp.server import TravelMCPServer
from app.ai.tools.registry import ToolRegistry


class FakeWeather:
    def get_forecast(self, location, days):
        return {"location": location, "days": [{"date": "2026-08-23", "precipitation_mm": 4}]}


class FakeMaps:
    def search_places(self, query, location, limit):
        return {"query": query, "places": [{"name": "Louvre"}]}


class FakeKnowledgeService:
    def search(self, query, destination=None, top_k=5):
        return []


class FakeLLMService:
    def generate_itinerary(self, destination, days, budget, travel_style, user_request=None, tool_context=None):
        return [{"day": 1, "activities": ["Louvre"]}]


def _server():
    return TravelMCPServer(
        handlers=TravelToolHandlers(
            weather_provider=FakeWeather(),
            maps_provider=FakeMaps(),
            calendar=TravelCalendarStore(),
        )
    )


def test_mcp_discovers_and_invokes_tools():
    client = InProcessMCPClient(server=_server())
    handshake = client.initialize()
    assert handshake["serverInfo"]["name"] == "vacation-travel-tools"
    names = {tool["name"] for tool in client.list_tools()}
    assert {"mcp_get_weather", "mcp_search_places", "mcp_add_calendar_event", "mcp_list_calendar_events"} <= names

    weather = client.call_tool("mcp_get_weather", {"location": "Paris", "days": 3})
    assert weather["structuredContent"]["location"] == "Paris"


def test_mcp_invalid_arguments():
    client = InProcessMCPClient(server=_server())
    with pytest.raises(MCPError) as exc:
        client.call_tool("mcp_get_weather", {})
    assert exc.value.code == "invalid"


def test_mcp_unknown_tool_and_unavailable_server():
    client = InProcessMCPClient(server=_server())
    with pytest.raises(MCPError) as exc:
        client.call_tool("mcp_book_flight", {"destination": "Paris"})
    assert exc.value.code == "unavailable"

    broken = FakeMCPClient(fail_list=True)
    with pytest.raises(MCPError) as exc:
        broken.list_tools()
    assert exc.value.code == "unavailable"

    failing = FakeMCPClient(fail_call=True)
    with pytest.raises(MCPError) as exc:
        failing.call_tool("mcp_get_weather", {"location": "Paris"})
    assert exc.value.code == "provider"


def test_mcp_calendar_round_trip():
    client = InProcessMCPClient(server=_server())
    created = client.call_tool(
        "mcp_add_calendar_event",
        {"title": "Louvre morning", "date": "2026-08-23", "destination": "Paris"},
    )
    listed = client.call_tool("mcp_list_calendar_events", {"destination": "Paris"})
    assert created["structuredContent"]["title"] == "Louvre morning"
    assert listed["structuredContent"]["count"] == 1


def test_agent_can_use_discovered_mcp_tools():
    client = InProcessMCPClient(server=_server())
    tools = discover_mcp_tools(client)
    model_responses = [
        AIMessage(
            content="",
            tool_calls=[{"name": "mcp_get_weather", "args": {"location": "Paris", "days": 2}, "id": "m1"}],
        ),
        AIMessage(content="done"),
    ]

    class ScriptedModel:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return model_responses.pop(0) if model_responses else AIMessage(content="")

    graph = PlanningGraph(
        model=ScriptedModel(),
        tools=tools,
        llm_service=FakeLLMService(),
        max_iterations=4,
    )
    result = graph.invoke({
        "messages": [],
        "user_request": "Plan Paris and check the weather via MCP.",
        "destination": "Paris",
        "days": 2,
        "budget": 1000,
        "trip_style": "budget",
        "tool_results": [],
        "tools_used": [],
        "warnings": [],
        "iteration": 0,
        "summary": "",
        "itinerary": [],
    })
    assert "mcp_get_weather" in result["tools_used"]
    assert result["itinerary"][0]["activities"] == ["Louvre"]


def test_tool_registry_attaches_mcp_tools(db_session):
    registry = ToolRegistry(FakeKnowledgeService(), mcp_client=InProcessMCPClient(server=_server()))
    names = {tool.name for tool in registry.all()}
    assert "get_weather" in names
    assert "mcp_get_weather" in names
    assert "mcp_add_calendar_event" in names


def test_tool_registry_survives_unavailable_mcp(db_session):
    registry = ToolRegistry(FakeKnowledgeService(), mcp_client=FakeMCPClient(fail_list=True))
    names = {tool.name for tool in registry.all()}
    assert "get_weather" in names
    assert "mcp_get_weather" not in names
    assert registry.mcp_warning
