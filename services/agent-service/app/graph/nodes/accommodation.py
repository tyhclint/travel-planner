from app.graph.state import TravelState
from app.services.accommodations.mock import MockAccommodationService

accommodation_service = MockAccommodationService()


def accommodation_node(state: TravelState):
    results = accommodation_service.search_accommodations(
        state["trip_requirements"],
        state["preferences"],
    )
    return {
        "accommodation_results": results,
        "task_status": {"accommodation": "completed"},
    }
