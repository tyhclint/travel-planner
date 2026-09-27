from langchain_core.messages import HumanMessage, SystemMessage

from app.domain.models.itinerary import ItineraryDay
from app.domain.models.recommendations import DestinationRecommendation
from app.graph.state import TravelState
from app.prompts.itinerary import ITINERARY_AGENT_SYSTEM_PROMPT, ITINERARY_AGENT_USER_PROMPT
from app.services.agent_history import agent_tool_history
from app.services.prompt_serialization import json_value


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
                trip_requirements=json_value(state.get("trip_requirements")),
                preferences=json_value(state.get("preferences")),
                selected_flight=json_value(state.get("selected_flight")),
                selected_accommodation=json_value(state.get("selected_accommodation")),
                itinerary_task_status=state.get("task_status", {}).get("itinerary"),
                planning_attempts=planning_attempts,
                research_results=json_value(research_results),
                validated_days=json_value(validated_days),
                current_itinerary=json_value(state.get("current_itinerary")),
                errors=json_value(state.get("errors", [])),
            )
        ),
        *agent_tool_history(state.get("messages", []), tool_names),
    ]
