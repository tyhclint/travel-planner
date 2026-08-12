from typing import Literal

from app.graph.state import TravelState

RouteName = Literal[
    "flight_agent",
    "accommodation_agent",
    "ranking",
    "web_search_agent",
    "itinerary_agent",
    "user_clarification",
    "response_agent",
]


def orchestrator_node(state: TravelState):
    return {"orchestration_steps": state.get("orchestration_steps", 0) + 1}


def route_orchestrator(state: TravelState) -> RouteName | list[RouteName]:
    if state.get("orchestration_steps", 0) > 10:
        return "response_agent"

    if state.get("missing_required_fields"):
        return "user_clarification"

    statuses = state.get("task_status", {})
    parallel_tasks: list[RouteName] = []

    if statuses.get("flight") in {"pending", "stale"}:
        parallel_tasks.append("flight_agent")

    if statuses.get("accommodation") in {"pending", "stale"}:
        parallel_tasks.append("accommodation_agent")

    if parallel_tasks:
        return parallel_tasks

    if statuses.get("ranking") in {"pending", "stale"}:
        return "ranking"

    if statuses.get("web_search") in {"pending", "stale"}:
        return "web_search_agent"

    if statuses.get("itinerary") in {"pending", "stale"}:
        return "itinerary_agent"

    return "response_agent"
