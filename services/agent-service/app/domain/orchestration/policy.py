from app.domain.models.errors import OrchestratorError
from app.domain.models.orchestrator import OrchestratorDecision, OrchestratorRoute
from app.domain.models.status import (
    RUNNABLE_TASK_STATUSES,
    TaskName,
    TaskStatus,
    normalize_task_status,
)
from app.graph.state import TravelState

MAX_ORCHESTRATION_STEPS = 10

ROUTE_TO_TASK: dict[OrchestratorRoute, TaskName | None] = {
    "flight_agent": "flight",
    "accommodation_agent": "accommodation",
    "itinerary_planner_agent": "itinerary",
    "user_clarification": None,
    "response_agent": None,
}


def deterministic_guardrail_decision(
    state: TravelState,
    orchestration_steps: int,
) -> OrchestratorDecision | None:
    """Return a mandatory deterministic decision for hard-stop or clarification cases."""
    if orchestration_steps >= MAX_ORCHESTRATION_STEPS:
        return OrchestratorDecision(
            next_tasks=["response_agent"],
            can_answer_now=True,
            reason="Maximum orchestration steps reached, so the graph should stop safely.",
        )

    missing_fields = state.get("missing_required_fields", [])
    if missing_fields:
        return OrchestratorDecision(
            next_tasks=["user_clarification"],
            needs_clarification=True,
            clarification_fields=missing_fields,
            reason="Required fields are missing before specialist work can continue.",
        )

    return None


def apply_deterministic_policy(
    state: TravelState,
    decision: OrchestratorDecision,
) -> OrchestratorDecision:
    """Reject unsafe LLM decisions so orchestrator_node can fail loudly or fall back."""
    statuses = normalize_task_status(state.get("task_status"))
    flight_is_runnable = statuses["flight"] in RUNNABLE_TASK_STATUSES
    itinerary_is_runnable = statuses["itinerary"] in RUNNABLE_TASK_STATUSES

    if decision.next_tasks == ["response_agent"] and has_runnable_required_work(statuses):
        raise OrchestratorError(
            "Orchestrator routed to response_agent while runnable work remains."
        )

    rerun_tasks = set(decision.rerun_completed_tasks)
    for route in decision.next_tasks:
        task_name = ROUTE_TO_TASK[route]
        if task_name is None:
            continue

        if statuses[task_name] == "completed" and task_name not in rerun_tasks:
            raise OrchestratorError(
                f"Orchestrator routed to {route} but {task_name} is already completed."
            )

    if (
        flight_is_runnable
        and itinerary_is_runnable
        and set(decision.next_tasks) != {"flight_agent", "itinerary_planner_agent"}
    ):
        raise OrchestratorError(
            "Orchestrator must route flight_agent and itinerary_planner_agent together "
            "when both flight and itinerary are runnable."
        )

    if (
        "accommodation_agent" in decision.next_tasks
        and any(
            statuses[task_name] in RUNNABLE_TASK_STATUSES
            for task_name in ("flight", "itinerary")
        )
    ):
        raise OrchestratorError(
            "Orchestrator routed to accommodation_agent before pending or stale flight "
            "and itinerary work completed."
        )

    return decision


def fallback_decision(
    state: TravelState,
    orchestration_steps: int,
) -> OrchestratorDecision:
    """Choose the next route using the deterministic task-status policy."""
    guardrail_decision = deterministic_guardrail_decision(state, orchestration_steps)
    if guardrail_decision:
        return guardrail_decision

    statuses = normalize_task_status(state.get("task_status"))
    flight_is_runnable = statuses["flight"] in RUNNABLE_TASK_STATUSES
    itinerary_is_runnable = statuses["itinerary"] in RUNNABLE_TASK_STATUSES

    if flight_is_runnable and itinerary_is_runnable:
        return OrchestratorDecision(
            next_tasks=["flight_agent", "itinerary_planner_agent"],
            reason="Flight and itinerary work are pending or stale and can run in parallel.",
        )

    if flight_is_runnable:
        return OrchestratorDecision(
            next_tasks=["flight_agent"],
            reason="Flight work is pending or stale.",
        )

    if itinerary_is_runnable:
        return OrchestratorDecision(
            next_tasks=["itinerary_planner_agent"],
            reason="Itinerary work is pending or stale.",
        )

    if statuses["accommodation"] in RUNNABLE_TASK_STATUSES:
        return OrchestratorDecision(
            next_tasks=["accommodation_agent"],
            reason="Accommodation work is pending or stale after itinerary planning completed.",
        )

    return OrchestratorDecision(
        next_tasks=["response_agent"],
        can_answer_now=True,
        reason="No runnable specialist work remains.",
    )


def has_runnable_required_work(statuses: dict[TaskName, TaskStatus]) -> bool:
    """Return whether any task is pending or stale."""
    return any(status in RUNNABLE_TASK_STATUSES for status in statuses.values())
