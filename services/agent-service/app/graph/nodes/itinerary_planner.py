from app.domain.models.itinerary import Activity, Itinerary, ItineraryDay
from app.graph.state import TravelState


def itinerary_planner_node(state: TravelState):
    requirements = state["trip_requirements"]
    preferences = state["preferences"]
    destination = requirements.destination or "your destination"
    day_count = requirements.trip_length_days or 3

    days = [
        ItineraryDay(
            day=day,
            title=f"Day {day} in {destination}",
            rationale=(
                "Grouped flexible food and sightseeing stops into the same day so the plan can "
                "later optimize around proximity and pace."
            ),
            activities=[
                Activity(
                    time="09:30",
                    title=f"{destination} neighborhood walk",
                    description=f"A {preferences.activity_pace} start with local food and sights.",
                    category="culture",
                    location=destination,
                    duration_minutes=150,
                    rationale="Starts the day with a low-friction activity near the destination core.",
                    url="https://example.com/destination-neighborhood-walk",
                ),
                Activity(
                    time="14:00",
                    title="Flexible highlight activity",
                    description="Use destination research results to swap in a real attraction later.",
                    category="highlight",
                    location=destination,
                    duration_minutes=180,
                    rationale="Leaves room for the planner to choose a researched attraction later.",
                    url="https://example.com/destination-highlight",
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
