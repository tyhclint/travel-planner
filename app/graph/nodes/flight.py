from app.graph.state import TravelState
from app.services.mcp.travel import MCPTravelService

flight_service = MCPTravelService()


def flight_node(state: TravelState):
    results = flight_service.search_flights(
        state["trip_requirements"],
        state["preferences"],
    )
    return {
        "flight_results": results,
        "task_status": {"flight": "completed"},
    }
