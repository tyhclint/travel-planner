import httpx

from app.core.config import get_gateway_settings


class DBServiceClient:
    def __init__(self, base_url: str | None = None):
        settings = get_gateway_settings()
        self.base_url = (base_url or settings.db_service_url).rstrip("/")

    async def list_trips(self, user_id: str | None = None) -> list[dict]:
        url = f"{self.base_url}/api/trips"
        params = {"user_id": user_id} if user_id else {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def create_trip(self, trip_data: dict) -> dict:
        url = f"{self.base_url}/api/trips"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=trip_data)
            response.raise_for_status()
            return response.json()

    async def get_trip(self, trip_id: str) -> dict:
        url = f"{self.base_url}/api/trips/{trip_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def update_trip(self, trip_id: str, trip_data: dict) -> dict:
        url = f"{self.base_url}/api/trips/{trip_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(url, json=trip_data)
            response.raise_for_status()
            return response.json()

    async def delete_trip(self, trip_id: str) -> dict:
        url = f"{self.base_url}/api/trips/{trip_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(url)
            response.raise_for_status()
            return response.json()

    async def check_health(self) -> dict:
        url = f"{self.base_url}/health"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            return response.json() if response.status_code == 200 else {"status": "unhealthy"}
