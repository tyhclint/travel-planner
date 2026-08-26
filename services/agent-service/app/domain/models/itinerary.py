from pydantic import BaseModel, Field


class Activity(BaseModel):
    time: str | None = None
    title: str
    description: str
    category: str | None = None
    location: str | None = None
    duration_minutes: int | None = None
    source_recommendation_id: str | None = None
    rationale: str | None = None
    url: str
    estimated_cost: float | None = None


class ItineraryDay(BaseModel):
    day: int
    title: str
    rationale: str = Field(
        description="Reasoning for why these activities were grouped on this day.",
    )
    activities: list[Activity] = Field(default_factory=list)


class Itinerary(BaseModel):
    destination: str
    days: list[ItineraryDay] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
