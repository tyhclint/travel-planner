import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_turn_interpreter_llm
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.domain.models.turn_interpreter import TurnInterpreterOutput
from app.domain.models.errors import TurnInterpreterError
from app.graph.state import TravelState
from app.prompts.turn_interpreter import (
    TURN_INTERPRETER_FEW_SHOTS,
    TURN_INTERPRETER_SYSTEM_PROMPT,
    TURN_INTERPRETER_USER_PROMPT,
)


def turn_interpreter_node(
    state: TravelState,
):
    latest_input = state.get("latest_user_input") or _latest_human_message(state)
    requirements = state.get("trip_requirements") or TripRequirements()
    preferences = state.get("preferences") or TravelPreferences()

    try:
        model = get_turn_interpreter_llm()
        structured_model = model.with_structured_output(TurnInterpreterOutput)
        extraction = TurnInterpreterOutput.model_validate(
            structured_model.invoke(_prompt_messages(state, latest_input, requirements, preferences))
        )
    except Exception as exc:
        raise TurnInterpreterError("Failed to interpret user turn.") from exc

    requirement_updates = _model_updates(extraction.trip_requirement_updates)
    preference_updates = _model_updates(extraction.preference_updates)

    return {
        "latest_user_input": latest_input,
        "turn_type": extraction.turn_type,
        "intent_summary": extraction.intent_summary,
        "requested_capabilities": _dedupe(extraction.requested_capabilities),
        "trip_requirement_updates": requirement_updates,
        "preference_updates": preference_updates,
        "constraints": _model_updates(extraction.constraints),
        "trip_requirements": requirements.model_copy(update=requirement_updates),
        "preferences": preferences.model_copy(update=preference_updates),
        "changed_fields": _dedupe(extraction.changed_fields),
        "revision_targets": [
            target.model_dump(exclude_none=True) for target in extraction.revision_targets
        ],
        "latest_feedback": _model_updates(extraction.latest_feedback),
        "missing_required_fields": _dedupe(extraction.missing_required_fields),
    }


def _prompt_messages(
    state: TravelState,
    latest_input: str,
    requirements: TripRequirements,
    preferences: TravelPreferences,
):
    return [
        SystemMessage(
            content=TURN_INTERPRETER_SYSTEM_PROMPT.format(
                few_shots=TURN_INTERPRETER_FEW_SHOTS
            )
        ),
        HumanMessage(
            content=TURN_INTERPRETER_USER_PROMPT.format(
                conversation_summary=state.get("conversation_summary", ""),
                trip_requirements=requirements.model_dump_json(),
                preferences=preferences.model_dump_json(),
                selected_flight=_json_value(state.get("selected_flight")),
                selected_accommodation=_json_value(state.get("selected_accommodation")),
                itinerary_summary=_json_value(state.get("current_itinerary")),
                latest_user_input=latest_input,
            )
        ),
    ]


def _model_updates(model) -> dict[str, Any]:
    return model.model_dump(exclude_none=True, exclude_defaults=True)


def _json_value(value: Any) -> str:
    if value is None:
        return "null"
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json()
    return json.dumps(value, default=str)


def _dedupe(values: list[Any]) -> list[Any]:
    deduped = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _latest_human_message(state: TravelState) -> str:
    for message in reversed(state.get("messages", [])):
        if getattr(message, "type", None) == "human":
            return str(message.content)
    return ""
