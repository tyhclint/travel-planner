from app.graph.state import TravelState
from app.services.mcp.travel import MCPTravelService

search_service = MCPTravelService()


def destination_research_node(state: TravelState):
    results = search_service.search_destination(
        state["trip_requirements"],
        state["preferences"],
    )
    return {
        "destination_research_results": results,
        "task_status": {"destination_research": "completed"},
    }
