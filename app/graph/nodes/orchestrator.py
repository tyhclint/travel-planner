import json
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.core.llm import get_orchestrator_llm
from app.domain.models.errors import AgentError, OrchestratorError
from app.domain.models.orchestrator import OrchestratorDecision
from app.domain.models.status import RUNNABLE_TASK_STATUSES, TaskName, TaskStatus, normalize_task_status
from app.graph.state import TravelState
from app.prompts.orchestrator import (
    ORCHESTRATOR_FEW_SHOTS,
    ORCHESTRATOR_SYSTEM_PROMPT,
    ORCHESTRATOR_USER_PROMPT,
)

RouteName = Literal[
    "flight_agent",
    "accommodation_agent",
    "destination_research_agent",
    "itinerary_planner_agent",
    "user_clarification",
    "response_agent",
]

MAX_ORCHESTRATION_STEPS = 10
MAX_ORCHESTRATOR_LLM_ATTEMPTS = 2

ROUTE_TO_TASK: dict[RouteName, TaskName | None] = {
    "flight_agent": "flight",
    "accommodation_agent": "accommodation",
    "destination_research_agent": "destination_research",
    "itinerary_planner_agent": "itinerary",
    "user_clarification": None,
    "response_agent": None,
}

PRESERVE_CONSTRAINTS: dict[TaskName, str] = {
    "flight": "preserve_flights",
    "accommodation": "preserve_accommodation",
    "destination_research": "preserve_destination_research",
    "itinerary": "preserve_itinerary",
}


def orchestrator_node(state: TravelState):
    """Create and store the next validated orchestration decision."""
    orchestration_steps = state.get("orchestration_steps", 0) + 1
    deterministic_decision = _deterministic_guardrail_decision(state, orchestration_steps)
    if deterministic_decision:
        return {
            "orchestration_steps": orchestration_steps,
            "orchestrator_decision": deterministic_decision.model_dump(),
        }

    errors: list[AgentError] = []
    try:
        decision = _validated_llm_decision(state, orchestration_steps)
        decision = _apply_deterministic_policy(state, decision)
    except Exception as exc:
        decision = _fallback_decision(state, orchestration_steps)
        errors.append(
            AgentError(
                source="orchestrator",
                error_type="llm_decision_failed",
                message=str(exc),
                retryable=False,
            )
        )

    update: dict[str, Any] = {
        "orchestration_steps": orchestration_steps,
        "orchestrator_decision": decision.model_dump(),
    }
    if errors:
        update["errors"] = errors

    return update


def route_orchestrator(state: TravelState) -> RouteName | list[RouteName]:
    """Translate the stored orchestration decision into LangGraph route names."""
    if state.get("orchestration_steps", 0) >= MAX_ORCHESTRATION_STEPS:
        return "response_agent"

    if state.get("missing_required_fields"):
        return "user_clarification"

    try:
        decision = OrchestratorDecision.model_validate(state.get("orchestrator_decision"))
    except ValidationError:
        decision = _fallback_decision(state, state.get("orchestration_steps", 0))

    if len(decision.next_tasks) == 1:
        return decision.next_tasks[0]

    return decision.next_tasks


def _validated_llm_decision(
    state: TravelState,
    orchestration_steps: int,
) -> OrchestratorDecision:
    """Ask the orchestrator LLM for structured output and validate it with Pydantic."""
    last_error: Exception | None = None

    for _ in range(MAX_ORCHESTRATOR_LLM_ATTEMPTS):
        try:
            model = get_orchestrator_llm()
            structured_model = model.with_structured_output(OrchestratorDecision)
            raw_decision = structured_model.invoke(_prompt_messages(state, orchestration_steps))
            return OrchestratorDecision.model_validate(raw_decision)
        except Exception as exc:
            last_error = exc

    raise OrchestratorError("Failed to produce a valid orchestrator decision.") from last_error


def _deterministic_guardrail_decision(
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


def _apply_deterministic_policy(
    state: TravelState,
    decision: OrchestratorDecision,
) -> OrchestratorDecision:
    """Reject unsafe LLM decisions and replace them with deterministic fallback routing."""

    statuses = normalize_task_status(state.get("task_status"))

    if decision.next_tasks == ["response_agent"] and _has_runnable_required_work(statuses):
        return _fallback_decision(state, state.get("orchestration_steps", 0))

    rerun_tasks = set(decision.rerun_completed_tasks)
    for route in decision.next_tasks:
        task_name = ROUTE_TO_TASK[route]
        if task_name is None:
            continue

        if _is_preserved_completed_task(state, task_name, statuses):
            return _fallback_decision(state, state.get("orchestration_steps", 0))

        if statuses[task_name] == "completed" and task_name not in rerun_tasks:
            return _fallback_decision(state, state.get("orchestration_steps", 0))

    return decision


def _fallback_decision(
    state: TravelState,
    orchestration_steps: int,
) -> OrchestratorDecision:
    """Choose the next route using the deterministic task-status policy."""

    guardrail_decision = _deterministic_guardrail_decision(state, orchestration_steps)
    if guardrail_decision:
        return guardrail_decision

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


def _prompt_messages(
    state: TravelState,
    orchestration_steps: int,
):
    """Build the system and user messages for the orchestrator LLM."""
    return [
        SystemMessage(
            content=ORCHESTRATOR_SYSTEM_PROMPT.format(
                few_shots=ORCHESTRATOR_FEW_SHOTS
            )
        ),
        HumanMessage(
            content=ORCHESTRATOR_USER_PROMPT.format(
                conversation_summary=state.get("conversation_summary", ""),
                latest_user_input=state.get("latest_user_input", ""),
                turn_interpretation=_json_value(_turn_interpretation(state)),
                trip_requirements=_json_value(state.get("trip_requirements")),
                preferences=_json_value(state.get("preferences")),
                task_status=_json_value(normalize_task_status(state.get("task_status"))),
                flight_results_summary=_json_value(state.get("flight_results", [])),
                accommodation_results_summary=_json_value(
                    state.get("accommodation_results", [])
                ),
                destination_research_summary=_json_value(
                    state.get("destination_research_results", [])
                ),
                selected_flight=_json_value(state.get("selected_flight")),
                selected_accommodation=_json_value(state.get("selected_accommodation")),
                itinerary_summary=_json_value(state.get("current_itinerary")),
                errors=_json_value(state.get("errors", [])),
                fan_in_notes=_json_value(state.get("fan_in_notes", [])),
                orchestration_steps=orchestration_steps,
                max_orchestration_steps=MAX_ORCHESTRATION_STEPS,
            )
        ),
    ]


def _turn_interpretation(state: TravelState) -> dict[str, Any]:
    """Collect turn-interpreter fields into a compact prompt payload."""
    return {
        "turn_type": state.get("turn_type"),
        "intent_summary": state.get("intent_summary"),
        "requested_capabilities": state.get("requested_capabilities", []),
        "trip_requirement_updates": state.get("trip_requirement_updates", {}),
        "preference_updates": state.get("preference_updates", {}),
        "constraints": state.get("constraints", {}),
        "changed_fields": state.get("changed_fields", []),
        "revision_targets": state.get("revision_targets", []),
        "latest_feedback": state.get("latest_feedback", {}),
        "missing_required_fields": state.get("missing_required_fields", []),
    }


def _has_runnable_required_work(statuses: dict[TaskName, TaskStatus]) -> bool:
    """Return whether any task is pending or stale."""
    return any(status in RUNNABLE_TASK_STATUSES for status in statuses.values())


def _is_preserved_completed_task(
    state: TravelState,
    task_name: TaskName,
    statuses: dict[TaskName, TaskStatus],
) -> bool:
    """Return whether a completed task is protected by a preservation constraint."""
    preserve_key = PRESERVE_CONSTRAINTS.get(task_name)
    return bool(
        preserve_key
        and state.get("constraints", {}).get(preserve_key)
        and statuses[task_name] == "completed"
    )


def _json_value(value: Any) -> str:
    """Serialize prompt values to JSON strings, including Pydantic models."""
    if value is None:
        return "null"
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json()
    if isinstance(value, list):
        return json.dumps([_json_safe(item) for item in value], default=str)
    return json.dumps(_json_safe(value), default=str)


def _json_safe(value: Any) -> Any:
    """Convert Pydantic models into JSON-serializable dictionaries."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value
