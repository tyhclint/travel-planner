from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_invoke_travel_route():
    mock_response = {
        "thread_id": "test-thread-123",
        "final_response": "Test travel recommendation",
        "task_status": {"flight": "completed"},
    }
    with patch("app.clients.agent_client.AgentServiceClient.invoke_travel_plan", new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = mock_response

        response = client.post(
            "/api/travel/invoke",
            json={"thread_id": "test-thread-123", "message": "Plan a trip to Tokyo"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "test-thread-123"
        assert "Test travel recommendation" in data["final_response"]


@pytest.mark.asyncio
async def test_search_flights_route():
    mock_flights = {
        "flights": [
            {
                "id": "f-1",
                "airline": "Mock Airlines",
                "origin": "Singapore",
                "destination": "Tokyo",
                "total_price": 450,
            }
        ]
    }
    with patch("app.clients.trip_client.TripServiceClient.search_flights", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_flights

        response = client.post(
            "/api/search/flights",
            json={"origin": "Singapore", "destination": "Tokyo"},
        )
        assert response.status_code == 200
        assert len(response.json()["flights"]) == 1
