from typing import Any

from langchain_core.messages import ToolMessage

from app.core.config import get_settings
from app.core.llm import get_accommodation_llm
from app.domain.models.accommodations import AccommodationOption
from app.domain.models.errors import AccommodationError, AgentError
from app.graph.state import TravelState
from app.services.accommodations.prompt_builder import build_accommodation_prompt_messages
from app.services.accommodations.result_parser import parse_accommodation_tool_messages
from app.services.accommodations.tools import (
    finish_accommodation_search,
    get_accommodation_details,
    get_accommodation_reviews,
    search_accommodations,
)
from app.services.agent_history import last_tool_message_name

MIN_USABLE_ACCOMMODATION_OPTIONS = 3
MAX_ACCOMMODATION_TOOL_ATTEMPTS = 5
ACCOMMODATION_TOOL_NAMES = {
    "search_accommodations",
    "get_accommodation_details",
    "get_accommodation_reviews",
    "finish_accommodation_search",
}
settings = get_settings()


def accommodation_node(state: TravelState):
    """Run the accommodation ReAct loop and populate accommodation_results."""
    messages = state.get("messages", [])
    accommodation_tool_messages = _tool_messages(messages)
    parsed_options = parse_accommodation_tool_messages(accommodation_tool_messages)

    if last_tool_message_name(messages) == "finish_accommodation_search":
        return _finalize_accommodation_results(parsed_options)

    if len(accommodation_tool_messages) >= MAX_ACCOMMODATION_TOOL_ATTEMPTS:
        return _finalize_accommodation_results(parsed_options)

    try:
        llm = get_accommodation_llm().bind_tools(
            [
                search_accommodations,
                get_accommodation_details,
                get_accommodation_reviews,
                finish_accommodation_search,
            ]
        )
        response = llm.invoke(
            build_accommodation_prompt_messages(
                state=state,
                tool_attempts=len(accommodation_tool_messages),
                parsed_options=parsed_options,
                min_accommodation_options=MIN_USABLE_ACCOMMODATION_OPTIONS,
                max_tool_attempts=MAX_ACCOMMODATION_TOOL_ATTEMPTS,
                tool_names=ACCOMMODATION_TOOL_NAMES,
            )
        )
    except RuntimeError as exc:
        error = AccommodationError(
            f"Accommodation agent could not choose the next accommodation action: {exc}"
        )
        if settings.debug:
            raise error from exc
        return _accommodation_failed_update(
            "llm_action_failed",
            str(error),
            retryable=True,
        )

    tool_calls = _known_tool_calls(getattr(response, "tool_calls", []) or [])
    if len(tool_calls) != 1:
        error = AccommodationError(
            "Accommodation agent must call exactly one accommodation tool."
        )
        if settings.debug:
            raise error
        return _accommodation_failed_update(
            "invalid_llm_action",
            str(error),
            retryable=True,
            messages=[response],
        )

    return {
        "messages": [response],
        "task_status": {"accommodation": "running"},
    }


def route_accommodation_agent(state: TravelState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "fan_in"

    tool_calls = getattr(messages[-1], "tool_calls", []) or []
    if _known_tool_calls(tool_calls):
        return "accommodation_tools"

    next_tasks = (state.get("orchestrator_decision") or {}).get("next_tasks", [])
    if "itinerary_planner_agent" in next_tasks:
        return "accommodation_done"

    return "fan_in"


def _known_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only tool calls that belong to this accommodation agent loop."""
    return [call for call in tool_calls if call.get("name") in ACCOMMODATION_TOOL_NAMES]


def _tool_messages(messages: list[Any]) -> list[ToolMessage]:
    """Filter graph messages down to ToolMessages for this accommodation loop."""
    return [
        message
        for message in messages
        if isinstance(message, ToolMessage) and message.name in ACCOMMODATION_TOOL_NAMES
    ]


def _finalize_accommodation_results(options: list[AccommodationOption]):
    """Create the final state update once accommodation search has reached a terminal action."""
    if options:
        return {
            "accommodation_results": options,
            "task_status": {"accommodation": "completed"},
        }

    return _accommodation_failed_update(
        "no_usable_accommodations",
        "Accommodation search completed but no usable accommodation options could be parsed.",
        retryable=True,
    )


def _accommodation_failed_update(
    error_type: str,
    message: str,
    *,
    retryable: bool,
    messages: list[Any] | None = None,
):
    """Build a failed accommodation-task update with a normalized AgentError."""
    update = {
        "task_status": {"accommodation": "failed"},
        "errors": [
            AgentError(
                source="accommodation",
                error_type=error_type,
                message=message,
                retryable=retryable,
            )
        ],
    }
    if messages:
        update["messages"] = messages
    return update
