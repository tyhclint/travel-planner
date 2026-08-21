from app.graph.state import TravelState
from app.domain.models.orchestrator import OrchestratorDecision, OrchestratorRoute
from app.domain.models.status import (
    RUNNABLE_TASK_STATUSES,
    TaskName,
    TaskStatus,
    normalize_task_status,
)

MAX_ORCHESTRATION_STEPS = 10

ROUTE_TO_TASK: dict[OrchestratorRoute, TaskName | None] = {
    "flight_agent": "flight",
    "accommodation_agent": "accommodation",
    "destination_research_agent": "destination_research",
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
    """Reject unsafe LLM decisions and replace them with deterministic fallback routing."""
    statuses = normalize_task_status(state.get("task_status"))

    if decision.next_tasks == ["response_agent"] and has_runnable_required_work(statuses):
        return fallback_decision(state, state.get("orchestration_steps", 0))

    rerun_tasks = set(decision.rerun_completed_tasks)
    for route in decision.next_tasks:
        task_name = ROUTE_TO_TASK[route]
        if task_name is None:
            continue

        if statuses[task_name] == "completed" and task_name not in rerun_tasks:
            return fallback_decision(state, state.get("orchestration_steps", 0))

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
    parallel_tasks: list[OrchestratorRoute] = []

    parallel_task_map: tuple[tuple[TaskName, OrchestratorRoute], ...] = (
        ("flight", "flight_agent"),
        ("accommodation", "accommodation_agent"),
        ("destination_research", "destination_research_agent"),
    )
    for task_name, route_name in parallel_task_map:
        if statuses[task_name] in RUNNABLE_TASK_STATUSES:
            parallel_tasks.append(route_name)

    if parallel_tasks:
        return OrchestratorDecision(
            next_tasks=parallel_tasks,
            reason="Runnable independent specialist tasks are pending or stale.",
        )

    if statuses["itinerary"] in RUNNABLE_TASK_STATUSES:
        return OrchestratorDecision(
            next_tasks=["itinerary_planner_agent"],
            reason="Itinerary work is pending or stale after upstream work completed.",
        )

    return OrchestratorDecision(
        next_tasks=["response_agent"],
        can_answer_now=True,
        reason="No runnable specialist work remains.",
    )


def has_runnable_required_work(statuses: dict[TaskName, TaskStatus]) -> bool:
    """Return whether any task is pending or stale."""
    return any(status in RUNNABLE_TASK_STATUSES for status in statuses.values())
