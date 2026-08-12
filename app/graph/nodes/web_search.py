from app.graph.state import TravelState
from app.services.search.mock import MockSearchService

search_service = MockSearchService()


def web_search_node(state: TravelState):
    results = search_service.search_destination(
        state["trip_requirements"],
        state["preferences"],
    )
    return {
        "web_search_results": results,
        "task_status": {"web_search": "completed"},
    }
