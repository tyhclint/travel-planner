from app.domain.models.itinerary import Activity, Itinerary, ItineraryDay
from app.graph.state import TravelState
from app.services.search.mock import MockSearchService

search_service = MockSearchService()


def itinerary_planner_node(state: TravelState):
    requirements = state["trip_requirements"]
    preferences = state["preferences"]
    destination = requirements.destination or "your destination"
    day_count = requirements.trip_length_days or 3
    destination_research_results = search_service.search_destination(
        requirements,
        preferences,
    )

    days = []
    for day in range(1, day_count + 1):
        highlight = destination_research_results[
            (day - 1) % len(destination_research_results)
        ]
        days.append(
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
                        description=(
                            f"A {preferences.activity_pace} start with local food and sights."
                        ),
                        category="culture",
                        location=destination,
                        duration_minutes=150,
                        rationale=(
                            "Starts the day with a low-friction activity near the destination core."
                        ),
                        url="https://example.com/destination-neighborhood-walk",
                    ),
                    Activity(
                        time="14:00",
                        title=highlight.name,
                        description=highlight.description,
                        category=highlight.category,
                        location=destination,
                        duration_minutes=180,
                        rationale=(
                            "Uses a researched destination candidate as the day's flexible highlight."
                        ),
                        url=highlight.source_url or "https://example.com/destination-highlight",
                    ),
                ],
            )
        )

    return {
        "destination_research_results": destination_research_results,
        "current_itinerary": Itinerary(
            destination=destination,
            days=days,
            assumptions=[
                (
                    "Mock destination research and itinerary generated before real "
                    "planning/provider integrations."
                )
            ],
        ),
        "itinerary_version": state.get("itinerary_version", 0) + 1,
        "task_status": {"itinerary": "completed"},
    }


def route_itinerary_planner(state: TravelState) -> str:
    next_tasks = (state.get("orchestrator_decision") or {}).get("next_tasks", [])
    if "flight_agent" in next_tasks:
        return "itinerary_done"

    return "fan_in"
