from pydantic import ValidationError

from app.core.config import get_settings
from app.domain.models.errors import AgentError, OrchestratorError
from app.domain.models.orchestrator import OrchestratorDecision, OrchestratorRoute
from app.domain.orchestration.policy import (
    MAX_ORCHESTRATION_STEPS,
    apply_deterministic_policy,
    deterministic_guardrail_decision,
    fallback_decision,
)
from app.graph.state import TravelState
from app.services.orchestration.llm import validated_llm_decision

RouteName = OrchestratorRoute
settings = get_settings()

def orchestrator_node(state: TravelState):
    """Create and store the next validated orchestration decision."""
    orchestration_steps = state.get("orchestration_steps", 0) + 1
    deterministic_decision = deterministic_guardrail_decision(state, orchestration_steps)
    if deterministic_decision:
        return {
            "orchestration_steps": orchestration_steps,
            "orchestrator_decision": deterministic_decision.model_dump(),
        }

    errors: list[AgentError] = []
    try:
        decision = validated_llm_decision(state, orchestration_steps)
        decision = apply_deterministic_policy(state, decision)
    except OrchestratorError as exc:
        if settings.debug:
            raise
        decision = fallback_decision(state, orchestration_steps)
        errors.append(
            AgentError(
                source="orchestrator",
                error_type="llm_decision_failed",
                message=str(exc),
                retryable=False,
            )
        )

    update = {
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
        decision = fallback_decision(state, state.get("orchestration_steps", 0))

    if len(decision.next_tasks) == 1:
        return decision.next_tasks[0]

    return decision.next_tasks
