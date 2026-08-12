from app.domain.models.itinerary import Activity, Itinerary, ItineraryDay
from app.graph.state import TravelState


def itinerary_node(state: TravelState):
    requirements = state["trip_requirements"]
    preferences = state["preferences"]
    destination = requirements.destination or "your destination"
    day_count = requirements.trip_length_days or 3

    days = [
        ItineraryDay(
            day=day,
            title=f"Day {day} in {destination}",
            activities=[
                Activity(
                    time="09:30",
                    title=f"{destination} neighborhood walk",
                    description=f"A {preferences.activity_pace} start with local food and sights.",
                ),
                Activity(
                    time="14:00",
                    title="Flexible highlight activity",
                    description="Use destination research results to swap in a real attraction later.",
                ),
            ],
        )
        for day in range(1, day_count + 1)
    ]

    return {
        "current_itinerary": Itinerary(
            destination=destination,
            days=days,
            assumptions=["Mock itinerary generated before real planning/provider integrations."],
        ),
        "itinerary_version": state.get("itinerary_version", 0) + 1,
        "task_status": {"itinerary": "completed"},
    }
