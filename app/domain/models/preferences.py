from typing import Literal

from pydantic import BaseModel, Field

Style = Literal["cheap", "standard", "luxurious"]


class TravelPreferences(BaseModel):
    overall_style: Style = "standard"
    flight_style: Style = "standard"
    accommodation_style: Style = "standard"
    flight_priority: Literal["cheapest", "most_convenient", "balanced"] = "balanced"
    accommodation_priority: Literal[
        "cheapest",
        "best_location",
        "most_luxurious",
        "balanced",
    ] = "balanced"
    activity_pace: Literal["relaxed", "balanced", "packed"] = "balanced"
    interests: list[str] = Field(default_factory=list)
