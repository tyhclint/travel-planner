import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.domain.models.flights import FlightOption
from app.graph.state import TravelState
from app.prompts.flight import FLIGHT_AGENT_SYSTEM_PROMPT, FLIGHT_AGENT_USER_PROMPT


def build_flight_prompt_messages(
    state: TravelState,
    *,
    search_attempts: int,
    parsed_options: list[FlightOption],
    min_flight_options: int,
    max_search_attempts: int,
    tool_names: set[str],
):
    """Build the messages for the flight agent LLM."""
    return [
        SystemMessage(
            content=FLIGHT_AGENT_SYSTEM_PROMPT.format(
                min_flight_options=min_flight_options,
                max_search_attempts=max_search_attempts,
            )
        ),
        HumanMessage(
            content=FLIGHT_AGENT_USER_PROMPT.format(
                conversation_summary=state.get("conversation_summary", ""),
                latest_user_input=state.get("latest_user_input", ""),
                trip_requirements=_json_value(state.get("trip_requirements")),
                preferences=_json_value(state.get("preferences")),
                flight_task_status=state.get("task_status", {}).get("flight"),
                search_attempts=search_attempts,
                usable_options=_json_value(parsed_options),
                errors=_json_value(state.get("errors", [])),
            )
        ),
        *_flight_agent_history(state.get("messages", []), tool_names),
    ]


def _flight_agent_history(messages: list[Any], tool_names: set[str]) -> list[Any]:
    """Keep prior flight AI/tool messages in order so tool-call IDs stay paired."""
    history: list[Any] = []
    for message in messages:
        if _known_tool_calls(getattr(message, "tool_calls", []) or [], tool_names) or (
            isinstance(message, ToolMessage) and message.name in tool_names
        ):
            history.append(message)
    return history


def _known_tool_calls(
    tool_calls: list[dict[str, Any]],
    tool_names: set[str],
) -> list[dict[str, Any]]:
    """Return only tool calls that belong to the provided tool-name set."""
    return [call for call in tool_calls if call.get("name") in tool_names]


def _json_value(value: Any) -> str:
    """Serialize prompt values to JSON, including Pydantic models."""
    if value is None:
        return "null"
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json()
    if isinstance(value, list):
        return json.dumps([_json_safe(item) for item in value], default=str)
    return json.dumps(_json_safe(value), default=str)


def _json_safe(value: Any) -> Any:
    """Convert Pydantic values into structures json.dumps can handle."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value
