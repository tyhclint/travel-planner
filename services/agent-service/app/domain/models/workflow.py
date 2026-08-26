from typing import Literal

TurnType = Literal[
    "new_plan",
    "revision",
    "follow_up_question",
    "presentation",
    "clarification_response",
]

RequestedCapability = Literal[
    "flight",
    "accommodation",
    "destination_research",
    "itinerary",
]

ChangedField = Literal[
    "origin",
    "destination",
    "travel_dates",
    "budget",
    "flight_preferences",
    "accommodation_preferences",
    "activity_preferences",
    "selected_flight",
    "selected_accommodation",
    "itinerary_day",
]
