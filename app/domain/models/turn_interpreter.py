from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.preferences import Style
from app.domain.models.workflow import ChangedField, RequestedCapability, TurnType


class TripRequirementUpdates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str | None = None
    destination: str | None = None
    departure_date: date | None = None
    return_date: date | None = None
    trip_length_days: int | None = Field(default=None, ge=1)
    travellers: int | None = Field(default=None, ge=1)
    budget: float | None = Field(default=None, ge=0)
    currency: str | None = None


class TravelPreferenceUpdates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_style: Style | None = None
    flight_style: Style | None = None
    accommodation_style: Style | None = None
    flight_priority: Literal["cheapest", "most_convenient", "balanced"] | None = None
    accommodation_priority: Literal[
        "cheapest",
        "best_location",
        "most_luxurious",
        "balanced",
    ] | None = None
    activity_pace: Literal["relaxed", "balanced", "packed"] | None = None
    interests: list[str] | None = None


class TurnConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preserve_flights: bool | None = None
    preserve_accommodation: bool | None = None
    preserve_destination_research: bool | None = None
    preserve_itinerary: bool | None = None
    preserve_unaffected_itinerary_days: bool | None = None


class RevisionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact: Literal["flight", "accommodation", "destination_research", "itinerary"]
    scope: Literal["full", "day", "item", "selection"]
    day: int | None = Field(default=None, ge=1)
    item: str | None = None


class LatestFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remove: list[str] = Field(default_factory=list)
    add: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    preserve: list[str] = Field(default_factory=list)
    instruction: str | None = None


class TurnInterpreterOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_type: TurnType
    intent_summary: str
    requested_capabilities: list[RequestedCapability]
    trip_requirement_updates: TripRequirementUpdates = Field(
        default_factory=TripRequirementUpdates
    )
    preference_updates: TravelPreferenceUpdates = Field(default_factory=TravelPreferenceUpdates)
    constraints: TurnConstraints = Field(default_factory=TurnConstraints)
    changed_fields: list[ChangedField] = Field(default_factory=list)
    revision_targets: list[RevisionTarget] = Field(default_factory=list)
    latest_feedback: LatestFeedback = Field(default_factory=LatestFeedback)
    missing_required_fields: list[str] = Field(default_factory=list)
