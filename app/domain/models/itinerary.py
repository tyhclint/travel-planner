from pydantic import BaseModel, Field


class Activity(BaseModel):
    time: str
    title: str
    description: str
    estimated_cost: float | None = None


class ItineraryDay(BaseModel):
    day: int
    title: str
    activities: list[Activity] = Field(default_factory=list)


class Itinerary(BaseModel):
    destination: str
    days: list[ItineraryDay] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
