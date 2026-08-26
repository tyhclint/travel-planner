import asyncio
from fastapi import APIRouter

from app.clients.agent_client import AgentServiceClient
from app.clients.db_client import DBServiceClient
from app.clients.trip_client import TripServiceClient

router = APIRouter(tags=["health"])
agent_client = AgentServiceClient()
db_client = DBServiceClient()
trip_client = TripServiceClient()


@router.get("/health")
async def health_check():
    agent_health, db_health, trip_health = await asyncio.gather(
        agent_client.check_health(),
        db_client.check_health(),
        trip_client.check_health(),
        return_exceptions=True,
    )

    def resolve(res):
        return res if isinstance(res, dict) else {"status": "unreachable"}

    return {
        "status": "ok",
        "service": "gateway",
        "downstream": {
            "agent_service": resolve(agent_health),
            "db_service": resolve(db_health),
            "trip_service": resolve(trip_health),
        },
    }
