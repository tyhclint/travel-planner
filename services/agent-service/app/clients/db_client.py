import httpx

from app.core.config import get_settings


class DBServiceClient:
    """HTTP client communicating with db-service microservice."""

    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.db_service_url).rstrip("/")

    def save_trip(self, trip_data: dict) -> dict | None:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(f"{self.base_url}/api/trips", json=trip_data)
                if response.status_code in (200, 201):
                    return response.json()
        except Exception:
            pass
        return None

    def get_trip(self, trip_id: str) -> dict | None:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/trips/{trip_id}")
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        return None
