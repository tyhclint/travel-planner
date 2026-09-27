import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.domain.models.itinerary import ItineraryDay
from app.domain.models.recommendations import DestinationRecommendation
from app.graph.state import TravelState
from app.prompts.itinerary import ITINERARY_AGENT_SYSTEM_PROMPT, ITINERARY_AGENT_USER_PROMPT
from app.services.agent_history import agent_tool_history


def build_itinerary_prompt_messages(
    state: TravelState,
    *,
    planning_attempts: int,
    research_results: list[DestinationRecommendation],
    validated_days: list[ItineraryDay],
    min_validated_days: int,
    max_planning_attempts: int,
    tool_names: set[str],
):
    """Build the messages for the itinerary planner LLM."""
    return [
        SystemMessage(
            content=ITINERARY_AGENT_SYSTEM_PROMPT.format(
                min_validated_days=min_validated_days,
                max_planning_attempts=max_planning_attempts,
            )
        ),
        HumanMessage(
            content=ITINERARY_AGENT_USER_PROMPT.format(
                conversation_summary=state.get("conversation_summary", ""),
                latest_user_input=state.get("latest_user_input", ""),
                trip_requirements=_json_value(state.get("trip_requirements")),
                preferences=_json_value(state.get("preferences")),
                selected_flight=_json_value(state.get("selected_flight")),
                selected_accommodation=_json_value(state.get("selected_accommodation")),
                itinerary_task_status=state.get("task_status", {}).get("itinerary"),
                planning_attempts=planning_attempts,
                research_results=_json_value(research_results),
                validated_days=_json_value(validated_days),
                current_itinerary=_json_value(state.get("current_itinerary")),
                errors=_json_value(state.get("errors", [])),
            )
        ),
        *agent_tool_history(state.get("messages", []), tool_names),
    ]


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
