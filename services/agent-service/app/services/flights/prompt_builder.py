from langchain_core.messages import HumanMessage, SystemMessage

from app.domain.models.flights import FlightOption
from app.graph.state import TravelState
from app.prompts.flight import FLIGHT_AGENT_SYSTEM_PROMPT, FLIGHT_AGENT_USER_PROMPT
from app.services.agent_history import agent_tool_history
from app.services.prompt_serialization import json_value


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
                trip_requirements=json_value(state.get("trip_requirements")),
                preferences=json_value(state.get("preferences")),
                flight_task_status=state.get("task_status", {}).get("flight"),
                search_attempts=search_attempts,
                usable_options=json_value(parsed_options),
                errors=json_value(state.get("errors", [])),
            )
        ),
        *agent_tool_history(state.get("messages", []), tool_names),
    ]
