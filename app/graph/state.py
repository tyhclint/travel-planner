from operator import add
from datetime import date
from typing import Annotated, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.domain.models.accommodations import AccommodationOption
from app.domain.models.errors import AgentError
from app.domain.models.flights import FlightOption
from app.domain.models.itinerary import Itinerary
from app.domain.models.preferences import Style, TravelPreferences
from app.domain.models.recommendations import DestinationRecommendation
from app.domain.models.status import TaskName, TaskStatus
from app.domain.models.trip import TripRequirements
from app.domain.models.turn_interpreter import RevisionTarget
from app.domain.models.workflow import ChangedField, RequestedCapability, TurnType


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    merged = dict(left or {})
    merged.update(right or {})
    return merged

class TripRequirementPatch(TypedDict, total=False):
    origin: str
    destination: str
    departure_date: date
    return_date: date
    trip_length_days: int
    travellers: int
    budget: float
    currency: str


class TravelPreferencePatch(TypedDict, total=False):
    overall_style: Style
    flight_style: Style
    accommodation_style: Style
    flight_priority: Literal["cheapest", "most_convenient", "balanced"]
    accommodation_priority: Literal[
        "cheapest",
        "best_location",
        "most_luxurious",
        "balanced",
    ]
    activity_pace: Literal["relaxed", "balanced", "packed"]
    interests: list[str]


class TurnConstraintPatch(TypedDict, total=False):
    pass


class TravelState(TypedDict, total=False):
    """Overall Stategraph State"""
    
    messages: Annotated[list[AnyMessage], add_messages]
    
    conversation_summary: str

    #turn interpreter results
    latest_user_input: str
    turn_type: TurnType
    intent_summary: str
    requested_capabilities: list[RequestedCapability]
    trip_requirement_updates: TripRequirementPatch
    preference_updates: TravelPreferencePatch
    constraints: TurnConstraintPatch
    trip_requirements: TripRequirements
    preferences: TravelPreferences
    changed_fields: list[ChangedField]
    revision_targets: list[RevisionTarget | dict]
    latest_feedback: dict
    # Used by the orchestrator to ask for clarification before calling subagents.
    missing_required_fields: list[str]


    #subagent results
    flight_results: list[FlightOption]
    accommodation_results: list[AccommodationOption]
    destination_research_results: list[DestinationRecommendation]

    ranked_flights: list[FlightOption]
    ranked_accommodations: list[AccommodationOption]
    selected_flight: FlightOption | None
    selected_accommodation: AccommodationOption | None

    current_itinerary: Itinerary | None
    itinerary_version: int

    task_status: Annotated[dict[TaskName, TaskStatus], merge_dicts]
    dispatched_tasks: list[str]
    orchestration_steps: int
    orchestrator_decision: dict
    revision_attempts: int
    errors: Annotated[list[AgentError], add]
    fan_in_notes: Annotated[list[str], add]

    final_response: str
