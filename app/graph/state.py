from operator import add
from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.domain.models.accommodations import AccommodationOption
from app.domain.models.errors import AgentError
from app.domain.models.flights import FlightOption
from app.domain.models.itinerary import Itinerary
from app.domain.models.preferences import TravelPreferences
from app.domain.models.recommendations import DestinationRecommendation
from app.domain.models.status import TaskStatus
from app.domain.models.trip import TripRequirements


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class TravelState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    latest_user_input: str
    conversation_summary: str

    turn_type: str
    requested_capabilities: list[str]
    requirement_updates: dict
    preference_updates: dict
    changed_fields: list[str]
    revision_targets: list[str]
    latest_feedback: dict
    missing_required_fields: list[str]

    trip_requirements: TripRequirements
    preferences: TravelPreferences

    flight_results: list[FlightOption]
    accommodation_results: list[AccommodationOption]
    web_search_results: list[DestinationRecommendation]

    ranked_flights: list[FlightOption]
    ranked_accommodations: list[AccommodationOption]
    recommended_packages: list[dict]
    selected_flight: FlightOption | None
    selected_accommodation: AccommodationOption | None

    current_itinerary: Itinerary | None
    itinerary_version: int

    task_status: Annotated[dict[str, TaskStatus], merge_dicts]
    dispatched_tasks: list[str]
    orchestration_steps: int
    revision_attempts: int
    errors: Annotated[list[AgentError], add]
    fan_in_notes: Annotated[list[str], add]

    final_response: str
