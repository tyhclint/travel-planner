from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_route():
    with patch("app.core.database.DatabaseManager.get_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.command.return_value = {"ok": 1}
        mock_get_db.return_value = mock_db

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "db-service"
