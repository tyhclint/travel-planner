from typing import Any
from pydantic import BaseModel, Field


class TravelRequest(BaseModel):
    thread_id: str = Field(..., min_length=1, description="Conversation thread identifier")
    message: str = Field(..., min_length=1, description="User prompt or follow-up instruction")


class TripCreateRequest(BaseModel):
    user_id: str = Field(default="anonymous")
    title: str = Field(..., min_length=1)
    destination: str
    origin: str | None = None
    trip_length_days: int = 3
    itinerary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str | None = None
    return_date: str | None = None
    cabin_class: str = "economy"
    currency: str = "USD"


class AccommodationSearchRequest(BaseModel):
    destination: str
    accommodation_style: str = "standard"
    accommodation_priority: str = "balanced"
    currency: str = "USD"


class DestinationResearchRequest(BaseModel):
    destination: str
    interests: list[str] = Field(default_factory=list)
    pace: str = "balanced"
