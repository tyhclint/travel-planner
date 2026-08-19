from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_flights():
    response = client.post(
        "/api/flights/search",
        json={"origin": "Singapore", "destination": "Tokyo", "cabin_class": "economy"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["origin"] == "Singapore"
    assert data["destination"] == "Tokyo"
    assert len(data["flights"]) > 0
    assert data["flights"][0]["airline"]


def test_search_accommodations():
    response = client.post(
        "/api/accommodations/search",
        json={"destination": "Tokyo", "accommodation_style": "standard"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["destination"] == "Tokyo"
    assert len(data["accommodations"]) > 0
    assert data["accommodations"][0]["name"]


def test_research_destinations():
    response = client.post(
        "/api/destinations/research",
        json={"destination": "Tokyo", "interests": ["culture", "food"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["destination"] == "Tokyo"
    assert len(data["recommendations"]) > 0


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
