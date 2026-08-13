from app.graph.state import TravelState
from app.services.search.mock import MockSearchService

search_service = MockSearchService()


def destination_research_node(state: TravelState):
    results = search_service.search_destination(
        state["trip_requirements"],
        state["preferences"],
    )
    return {
        "destination_research_results": results,
        "task_status": {"destination_research": "completed"},
    }
