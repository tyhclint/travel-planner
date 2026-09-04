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


def route_flight_agent(state: TravelState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "fan_in"

    last_message = messages[-1]
    if getattr(last_message, "tool_calls", None):
        return "flight_tools"

    return "fan_in"
