from typing import Any

from langchain_core.messages import ToolMessage

from app.core.llm import get_itinerary_llm
from app.domain.models.errors import AgentError, LLMProviderError
from app.domain.models.itinerary import Itinerary, ItineraryDay
from app.domain.models.recommendations import DestinationRecommendation
from app.graph.state import TravelState
from app.services.agent_history import last_tool_message_name
from app.services.itinerary.prompt_builder import build_itinerary_prompt_messages
from app.services.itinerary.result_parser import (
    parse_destination_research_tool_messages,
    parse_validated_day_plan_tool_messages,
)
from app.services.itinerary.tools import (
    destination_research_tool,
    finish_itinerary_planning,
    validate_day_plan,
)

MIN_VALIDATED_ITINERARY_DAYS = 1
MAX_ITINERARY_PLANNING_ATTEMPTS = 6
ITINERARY_TOOL_NAMES = {
    "destination_research_tool",
    "validate_day_plan",
    "finish_itinerary_planning",
}


def itinerary_planner_node(state: TravelState):
    """Run the itinerary ReAct loop and populate current_itinerary after completion."""
    messages = state.get("messages", [])
    research_tool_messages = _tool_messages(messages, "destination_research_tool")
    validation_tool_messages = _tool_messages(messages, "validate_day_plan")
    parsed_research = parse_destination_research_tool_messages(research_tool_messages)
    validated_days = parse_validated_day_plan_tool_messages(validation_tool_messages)

    if last_tool_message_name(messages) == "finish_itinerary_planning":
        return _finalize_itinerary(state, parsed_research, validated_days)

    planning_attempts = len(research_tool_messages) + len(validation_tool_messages)
    if planning_attempts >= MAX_ITINERARY_PLANNING_ATTEMPTS:
        return _finalize_itinerary(state, parsed_research, validated_days)

    
    llm = get_itinerary_llm().bind_tools(
        [destination_research_tool, validate_day_plan, finish_itinerary_planning]
    )
    response = llm.invoke(
        build_itinerary_prompt_messages(
            state=state,
            planning_attempts=planning_attempts,
            research_results=parsed_research,
            validated_days=validated_days,
            min_validated_days=MIN_VALIDATED_ITINERARY_DAYS,
            max_planning_attempts=MAX_ITINERARY_PLANNING_ATTEMPTS,
            tool_names=ITINERARY_TOOL_NAMES,
        )
    )

    tool_calls = _known_tool_calls(getattr(response, "tool_calls", []) or [])
    if len(tool_calls) != 1:
        return _itinerary_failed_update(
            "invalid_llm_action",
            "Itinerary planner must call exactly one itinerary tool.",
            retryable=True,
            messages=[response],
        )

    return {
        "messages": [response],
        "task_status": {"itinerary": "running"},
    }


def route_itinerary_planner(state: TravelState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "fan_in"

    tool_calls = getattr(messages[-1], "tool_calls", []) or []
    if _known_tool_calls(tool_calls):
        return "itinerary_tools"

    next_tasks = (state.get("orchestrator_decision") or {}).get("next_tasks", [])
    if "flight_agent" in next_tasks:
        return "itinerary_done"

    return "fan_in"


def _known_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only tool calls that belong to this itinerary agent loop."""
    return [call for call in tool_calls if call.get("name") in ITINERARY_TOOL_NAMES]


def _tool_messages(messages: list[Any], name: str) -> list[ToolMessage]:
    """Filter graph messages down to ToolMessages with the requested tool name."""
    return [
        message
        for message in messages
        if isinstance(message, ToolMessage) and message.name == name
    ]


def _finalize_itinerary(
    state: TravelState,
    research_results: list[DestinationRecommendation],
    validated_days: list[ItineraryDay],
):
    """Create the final state update once itinerary planning has reached a terminal action."""
    if validated_days:
        requirements = state.get("trip_requirements")
        destination = getattr(requirements, "destination", None) or "your destination"
        return {
            "destination_research_results": research_results,
            "current_itinerary": Itinerary(
                destination=destination,
                days=validated_days,
                assumptions=[
                    (
                        "Itinerary generated with mock destination tools; provider data can be "
                        "replaced when the itinerary MCP server is available."
                    )
                ],
            ),
            "itinerary_version": state.get("itinerary_version", 0) + 1,
            "task_status": {"itinerary": "completed"},
        }

    return _itinerary_failed_update(
        "no_validated_itinerary_days",
        "Itinerary planning completed but no validated day plans could be parsed.",
        retryable=True,
    )


def _itinerary_failed_update(
    error_type: str,
    message: str,
    *,
    retryable: bool,
    messages: list[Any] | None = None,
):
    """Build a failed itinerary-task update with a normalized AgentError."""
    update = {
        "task_status": {"itinerary": "failed"},
        "errors": [
            AgentError(
                source="itinerary",
                error_type=error_type,
                message=message,
                retryable=retryable,
            )
        ],
    }
    if messages:
        update["messages"] = messages
    return update
