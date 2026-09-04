from typing import Any, Mapping

from app.core.llm import get_orchestrator_llm
from app.domain.models.errors import OrchestratorError
from app.domain.models.orchestrator import OrchestratorDecision
from app.services.orchestration.prompt_builder import build_orchestrator_prompt_messages

MAX_ORCHESTRATOR_LLM_ATTEMPTS = 2


def validated_llm_decision(
    state: Mapping[str, Any],
    orchestration_steps: int,
) -> OrchestratorDecision:
    """Ask the orchestrator LLM for structured output and validate it with Pydantic."""
    last_error: Exception | None = None

    for _ in range(MAX_ORCHESTRATOR_LLM_ATTEMPTS):
        try:
            model = get_orchestrator_llm()
            structured_model = model.with_structured_output(OrchestratorDecision)
            raw_decision = structured_model.invoke(
                build_orchestrator_prompt_messages(state, orchestration_steps)
            )
            return OrchestratorDecision.model_validate(raw_decision)
        except Exception as exc:
            last_error = exc

    raise OrchestratorError("Failed to produce a valid orchestrator decision.") from last_error
