import httpx

from app.core.config import get_gateway_settings


class TripServiceClient:
    def __init__(self, base_url: str | None = None):
        settings = get_gateway_settings()
        self.base_url = (base_url or settings.trip_service_url).rstrip("/")

    async def search_flights(self, params: dict) -> dict:
        url = f"{self.base_url}/api/flights/search"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=params)
            response.raise_for_status()
            return response.json()

    async def search_accommodations(self, params: dict) -> dict:
        url = f"{self.base_url}/api/accommodations/search"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=params)
            response.raise_for_status()
            return response.json()

    async def research_destinations(self, params: dict) -> dict:
        url = f"{self.base_url}/api/destinations/research"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=params)
            response.raise_for_status()
            return response.json()

    async def check_health(self) -> dict:
        url = f"{self.base_url}/health"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            return response.json() if response.status_code == 200 else {"status": "unhealthy"}
