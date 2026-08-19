from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_health_check_aggregated():
    with (
        patch("app.clients.agent_client.AgentServiceClient.check_health", new_callable=AsyncMock) as mock_agent,
        patch("app.clients.db_client.DBServiceClient.check_health", new_callable=AsyncMock) as mock_db,
        patch("app.clients.trip_client.TripServiceClient.check_health", new_callable=AsyncMock) as mock_trip,
    ):
        mock_agent.return_value = {"status": "ok", "service": "agent-service"}
        mock_db.return_value = {"status": "ok", "service": "db-service"}
        mock_trip.return_value = {"status": "ok", "service": "trip-service"}

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "gateway"
        assert data["downstream"]["agent_service"]["status"] == "ok"
