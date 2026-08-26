from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas import TravelRequest
from app.clients.agent_client import AgentServiceClient

router = APIRouter(prefix="/travel", tags=["travel"])
agent_client = AgentServiceClient()


@router.post("/stream")
async def stream_travel_plan(request: TravelRequest) -> StreamingResponse:
    """Streams LangGraph agent updates back to Next.js via ndjson."""
    try:
        stream_generator = agent_client.stream_travel_plan(request.thread_id, request.message)
        return StreamingResponse(stream_generator, media_type="application/x-ndjson")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect to agent service: {e}") from e


@router.post("/invoke")
async def invoke_travel_plan(request: TravelRequest):
    """Invokes the LangGraph agent synchronously and returns the complete final state."""
    try:
        return await agent_client.invoke_travel_plan(request.thread_id, request.message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent service error: {e}") from e
