from typing import Literal

from app.domain.models.status import RUNNABLE_TASK_STATUSES, TaskName, normalize_task_status
from app.graph.state import TravelState

RouteName = Literal[
    "flight_agent",
    "accommodation_agent",
    "destination_research_agent",
    "ranking",
    "itinerary_planner_agent",
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

    statuses = normalize_task_status(state.get("task_status"))
    parallel_tasks: list[RouteName] = []

    parallel_task_map: tuple[tuple[TaskName, RouteName], ...] = (
        ("flight", "flight_agent"),
        ("accommodation", "accommodation_agent"),
        ("destination_research", "destination_research_agent"),
    )
    for task_name, route_name in parallel_task_map:
        if statuses[task_name] in RUNNABLE_TASK_STATUSES:
            parallel_tasks.append(route_name)

    if parallel_tasks:
        return parallel_tasks

    if statuses["ranking"] in RUNNABLE_TASK_STATUSES:
        return "ranking"

    if statuses["itinerary"] in RUNNABLE_TASK_STATUSES:
        return "itinerary_planner_agent"

    return "response_agent"
