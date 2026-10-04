from uuid import uuid4

from app.controllers import planning as planning_controller


class FakePlanningService:
    def __init__(self, db=None):
        self.db = db

    def plan_trip(self, user_id, request):
        if request.message == "missing-trip":
            raise ValueError("Trip not found")
        if request.message == "llm-down":
            raise RuntimeError("LLM_API_KEY is not configured")
        return {
            "trip_id": request.trip_id,
            "destination": request.destination or "Paris",
            "summary": "A weather-aware Paris plan",
            "itinerary": [{"day": 1, "activities": ["Musee d'Orsay"]}],
            "tools_used": ["get_weather", "search_travel_knowledge"],
            "warnings": [],
            "message": "Trip plan generated successfully",
        }


def test_planning_request_validation(auth_client):
    response = auth_client.post("/planning/", json={"message": ""})
    assert response.status_code == 422


def test_planning_success(auth_client, monkeypatch):
    monkeypatch.setattr(planning_controller, "PlanningService", FakePlanningService)
    response = auth_client.post("/planning/", json={
        "message": "Plan my Paris trip and include weather-friendly activities.",
        "destination": "Paris",
        "days": 3,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["destination"] == "Paris"
    assert body["tools_used"] == ["get_weather", "search_travel_knowledge"]
    assert body["itinerary"][0]["day"] == 1


def test_planning_trip_not_found(auth_client, monkeypatch):
    monkeypatch.setattr(planning_controller, "PlanningService", FakePlanningService)
    response = auth_client.post("/planning/", json={"message": "missing-trip", "trip_id": str(uuid4())})
    assert response.status_code == 404


def test_planning_llm_unavailable(auth_client, monkeypatch):
    monkeypatch.setattr(planning_controller, "PlanningService", FakePlanningService)
    response = auth_client.post("/planning/", json={"message": "llm-down"})
    assert response.status_code == 503


def test_planning_requires_auth(client):
    response = client.post("/planning/", json={"message": "Plan a trip"})
    assert response.status_code in {401, 403}


def test_existing_generate_ai_endpoint_uses_planning_service(auth_client, monkeypatch):
    from app.controllers import itinerary as itinerary_controller

    class FakePlanningService:
        def __init__(self, db=None):
            self.db = db

        def plan_trip(self, user_id, request):
            return {
                "trip_id": request.trip_id,
                "destination": "Paris",
                "summary": "A 3-day plan for Paris",
                "itinerary": [{"day": 1, "activities": ["Louvre"]}],
                "tools_used": ["search_travel_knowledge"],
                "warnings": [],
                "message": "Trip plan generated and itinerary saved",
            }

    monkeypatch.setattr(itinerary_controller, "PlanningService", FakePlanningService)
    response = auth_client.post(
        f"/itineraries/{uuid4()}/generate-ai",
        json={"message": "Include weather-friendly activities"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["itinerary"][0]["activities"] == ["Louvre"]
    assert "itinerary" in body
