from app.graph.state import TravelState
from app.services.mcp.travel import MCPTravelService

accommodation_service = MCPTravelService()


def accommodation_node(state: TravelState):
    results = accommodation_service.search_accommodations(
        state["trip_requirements"],
        state["preferences"],
    )
    return {
        "accommodation_results": results,
        "task_status": {"accommodation": "completed"},
    }
