from typing import Any

from langchain_core.messages import ToolMessage

from app.core.llm import get_flight_llm
from app.domain.models.errors import AgentError
from app.domain.models.flights import FlightOption
from app.graph.state import TravelState
from app.services.flights.prompt_builder import build_flight_prompt_messages
from app.services.flights.result_parser import parse_flight_tool_messages
from app.services.flights.tools import finish_flight_search, search_flights

MIN_USABLE_FLIGHT_OPTIONS = 3
MAX_FLIGHT_SEARCH_ATTEMPTS = 3
FLIGHT_TOOL_NAMES = {"search_flights", "finish_flight_search"}


def flight_node(state: TravelState):
    """Run the flight ReAct loop and populate flight_results after a terminal action."""
    messages = state.get("messages", [])
    search_tool_messages = _tool_messages(messages, "search_flights")
    parsed_options = parse_flight_tool_messages(search_tool_messages)

    if _last_tool_message_name(messages) == "finish_flight_search":
        return _finalize_flight_results(parsed_options)

    if len(search_tool_messages) >= MAX_FLIGHT_SEARCH_ATTEMPTS:
        return _finalize_flight_results(parsed_options)

    try:
        llm = get_flight_llm().bind_tools([search_flights, finish_flight_search])
        response = llm.invoke(
            build_flight_prompt_messages(
                state=state,
                search_attempts=len(search_tool_messages),
                parsed_options=parsed_options,
                min_flight_options=MIN_USABLE_FLIGHT_OPTIONS,
                max_search_attempts=MAX_FLIGHT_SEARCH_ATTEMPTS,
                tool_names=FLIGHT_TOOL_NAMES,
            )
        )
    except RuntimeError as exc:
        return _flight_failed_update(
            "llm_action_failed",
            f"Flight agent could not choose the next flight action: {exc}",
            retryable=True,
        )

    tool_calls = _known_tool_calls(getattr(response, "tool_calls", []) or [])
    if len(tool_calls) != 1:
        return _flight_failed_update(
            "invalid_llm_action",
            "Flight agent must call exactly one flight tool.",
            retryable=True,
            messages=[response],
        )

    return {
        "messages": [response],
        "task_status": {"flight": "running"},
    }


def route_flight_agent(state: TravelState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "fan_in"

    tool_calls = getattr(messages[-1], "tool_calls", []) or []
    if _known_tool_calls(tool_calls):
        return "flight_tools"

    return "fan_in"


def _known_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only tool calls that belong to this flight agent loop."""
    return [call for call in tool_calls if call.get("name") in FLIGHT_TOOL_NAMES]


def _tool_messages(messages: list[Any], name: str) -> list[ToolMessage]:
    """Filter graph messages down to ToolMessages with the requested tool name."""
    return [
        message
        for message in messages
        if isinstance(message, ToolMessage) and message.name == name
    ]


def _last_tool_message_name(messages: list[Any]) -> str | None:
    """Return the name of the latest message when it is a ToolMessage."""
    if messages and isinstance(messages[-1], ToolMessage):
        return messages[-1].name
    return None


def _finalize_flight_results(options: list[FlightOption]):
    """Create the final state update once flight search has reached a terminal action."""
    if options:
        return {
            "flight_results": options,
            "task_status": {"flight": "completed"},
        }

    return _flight_failed_update(
        "no_usable_flights",
        "Flight search completed but no usable flight options could be parsed.",
        retryable=True,
    )


def _flight_failed_update(
    error_type: str,
    message: str,
    *,
    retryable: bool,
    messages: list[Any] | None = None,
):
    """Build a failed flight-task update with a normalized AgentError."""
    update = {
        "task_status": {"flight": "failed"},
        "errors": [
            AgentError(
                source="flight",
                error_type=error_type,
                message=message,
                retryable=retryable,
            )
        ],
    }
    if messages:
        update["messages"] = messages
    return update
