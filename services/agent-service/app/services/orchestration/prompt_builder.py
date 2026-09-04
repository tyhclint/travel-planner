import json
from typing import Any, Mapping

from langchain_core.messages import HumanMessage, SystemMessage

from app.domain.models.status import normalize_task_status
from app.domain.orchestration.policy import MAX_ORCHESTRATION_STEPS
from app.prompts.orchestrator import (
    ORCHESTRATOR_FEW_SHOTS,
    ORCHESTRATOR_SYSTEM_PROMPT,
    ORCHESTRATOR_USER_PROMPT,
)


def build_orchestrator_prompt_messages(
    state: Mapping[str, Any],
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
                turn_interpretation=json_value(turn_interpretation_payload(state)),
                trip_requirements=json_value(state.get("trip_requirements")),
                preferences=json_value(state.get("preferences")),
                task_status=json_value(normalize_task_status(state.get("task_status"))),
                flight_results_summary=json_value(state.get("flight_results", [])),
                accommodation_results_summary=json_value(
                    state.get("accommodation_results", [])
                ),
                destination_research_summary=json_value(
                    state.get("destination_research_results", [])
                ),
                selected_flight=json_value(state.get("selected_flight")),
                selected_accommodation=json_value(state.get("selected_accommodation")),
                itinerary_summary=json_value(state.get("current_itinerary")),
                errors=json_value(state.get("errors", [])),
                fan_in_notes=json_value(state.get("fan_in_notes", [])),
                orchestration_steps=orchestration_steps,
                max_orchestration_steps=MAX_ORCHESTRATION_STEPS,
            )
        ),
    ]


def turn_interpretation_payload(state: Mapping[str, Any]) -> dict[str, Any]:
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


def json_value(value: Any) -> str:
    """Serialize prompt values to JSON strings, including Pydantic models."""
    if value is None:
        return "null"
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json()
    if isinstance(value, list):
        return json.dumps([json_safe(item) for item in value], default=str)
    return json.dumps(json_safe(value), default=str)


def json_safe(value: Any) -> Any:
    """Convert Pydantic models into JSON-serializable dictionaries."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value
