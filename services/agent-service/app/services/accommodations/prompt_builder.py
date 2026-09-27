from langchain_core.messages import HumanMessage, SystemMessage

from app.domain.models.accommodations import AccommodationOption
from app.graph.state import TravelState
from app.prompts.accommodation import (
    ACCOMMODATION_AGENT_SYSTEM_PROMPT,
    ACCOMMODATION_AGENT_USER_PROMPT,
)
from app.services.agent_history import agent_tool_history
from app.services.prompt_serialization import json_value


def build_accommodation_prompt_messages(
    state: TravelState,
    *,
    tool_attempts: int,
    parsed_options: list[AccommodationOption],
    min_accommodation_options: int,
    max_tool_attempts: int,
    tool_names: set[str],
):
    """Build the messages for the accommodation agent LLM."""
    return [
        SystemMessage(
            content=ACCOMMODATION_AGENT_SYSTEM_PROMPT.format(
                min_accommodation_options=min_accommodation_options,
                max_tool_attempts=max_tool_attempts,
            )
        ),
        HumanMessage(
            content=ACCOMMODATION_AGENT_USER_PROMPT.format(
                conversation_summary=state.get("conversation_summary", ""),
                latest_user_input=state.get("latest_user_input", ""),
                trip_requirements=json_value(state.get("trip_requirements")),
                preferences=json_value(state.get("preferences")),
                selected_flight=json_value(state.get("selected_flight")),
                accommodation_task_status=state.get("task_status", {}).get("accommodation"),
                tool_attempts=tool_attempts,
                usable_options=json_value(parsed_options),
                errors=json_value(state.get("errors", [])),
            )
        ),
        *agent_tool_history(state.get("messages", []), tool_names),
    ]
