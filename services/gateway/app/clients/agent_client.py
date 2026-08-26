from collections.abc import AsyncIterator
import httpx

from app.core.config import get_gateway_settings


class AgentServiceClient:
    def __init__(self, base_url: str | None = None):
        settings = get_gateway_settings()
        self.base_url = (base_url or settings.agent_service_url).rstrip("/")

    async def stream_travel_plan(self, thread_id: str, message: str) -> AsyncIterator[bytes]:
        url = f"{self.base_url}/api/travel/stream"
        payload = {"thread_id": thread_id, "message": message}
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    async def invoke_travel_plan(self, thread_id: str, message: str) -> dict:
        url = f"{self.base_url}/api/travel/invoke"
        payload = {"thread_id": thread_id, "message": message}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def check_health(self) -> dict:
        url = f"{self.base_url}/health"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            return response.json() if response.status_code == 200 else {"status": "unhealthy"}
