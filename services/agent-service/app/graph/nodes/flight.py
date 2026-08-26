from app.graph.state import TravelState
from app.services.flights.mock import MockFlightService

flight_service = MockFlightService()


def flight_node(state: TravelState):
    results = flight_service.search_flights(
        state["trip_requirements"],
        state["preferences"],
    )
    return {
        "flight_results": results,
        "task_status": {"flight": "completed"},
    }
