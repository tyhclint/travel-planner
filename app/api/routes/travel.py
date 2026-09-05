import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.api.schemas import TravelPlanResponse, TravelStreamRequest
from app.graph.builder import get_graph
from app.services.mcp.workflow import run_travel_turn

router = APIRouter(prefix="/travel", tags=["travel"])


@router.post("/plan", response_model=TravelPlanResponse)
def plan_travel(request: TravelStreamRequest) -> TravelPlanResponse:
    response = run_travel_turn(request.message, request.thread_id)
    return TravelPlanResponse(thread_id=request.thread_id, response=response)


@router.post("/stream")
async def stream_travel_plan(request: TravelStreamRequest) -> StreamingResponse:
    graph = get_graph()

    async def events() -> AsyncIterator[str]:
        graph_input = {
            "messages": [HumanMessage(content=request.message)],
            "latest_user_input": request.message,
        }
        config = {"configurable": {"thread_id": request.thread_id}}

        async for update in graph.astream(graph_input, config=config, stream_mode="updates"):
            yield json.dumps(update, default=str) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")
