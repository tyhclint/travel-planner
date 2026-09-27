from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.domain.models.itinerary import Activity, ItineraryDay
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.services.search.mock import MockSearchService

ActivityCategoryInput = Literal[
    "culture",
    "food",
    "nature",
    "shopping",
    "nightlife",
    "transport",
    "rest",
    "other",
]


class DestinationResearchArgs(BaseModel):
    destination: str = Field(..., min_length=1, max_length=120)
    interests: list[str] = Field(default_factory=list, max_length=12)
    trip_length_days: int = Field(default=3, ge=1, le=30)
    budget: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    pace: Literal["relaxed", "balanced", "packed"] = "balanced"


class DayPlanActivityInput(BaseModel):
    time: str | None = Field(default=None, max_length=20)
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(..., min_length=1, max_length=1000)
    category: ActivityCategoryInput = "other"
    location: str | None = Field(default=None, max_length=200)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    source_recommendation_id: str | None = Field(default=None, max_length=160)
    rationale: str | None = Field(default=None, max_length=1000)
    url: str | None = Field(default=None, max_length=1000)
    estimated_cost: float | None = Field(default=None, ge=0)


class ValidateDayPlanArgs(BaseModel):
    day: int = Field(..., ge=1, le=30)
    title: str = Field(..., min_length=1, max_length=160)
    rationale: str = Field(..., min_length=1, max_length=1000)
    activities: list[DayPlanActivityInput] = Field(..., min_length=1, max_length=12)


class FinishItineraryPlanningArgs(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


_mock_search_service = MockSearchService()


@tool(args_schema=DestinationResearchArgs)
def destination_research_tool(
    destination: str,
    interests: list[str] | None = None,
    trip_length_days: int = 3,
    budget: float | None = None,
    currency: str = "USD",
    pace: Literal["relaxed", "balanced", "packed"] = "balanced",
) -> dict:
    """Return mock destination recommendations using the app-owned research schema."""
    requirements = TripRequirements(
        destination=destination,
        trip_length_days=trip_length_days,
        budget=budget,
        currency=currency.upper(),
    )
    preferences = TravelPreferences(
        interests=interests or [],
        activity_pace=pace,
    )
    recommendations = _mock_search_service.search_destination(requirements, preferences)

    return {
        "provider": "mock",
        "destination": destination,
        "recommendations": [
            recommendation.model_dump(mode="json") for recommendation in recommendations
        ],
    }


@tool(args_schema=ValidateDayPlanArgs)
def validate_day_plan(
    day: int,
    title: str,
    rationale: str,
    activities: list[DayPlanActivityInput],
) -> dict:
    """Validate and normalize one itinerary day plan."""
    normalized_activities = [
        Activity(
            time=_activity_value(activity, "time"),
            title=_activity_value(activity, "title"),
            description=_activity_value(activity, "description"),
            category=_activity_value(activity, "category"),
            location=_activity_value(activity, "location"),
            duration_minutes=_activity_value(activity, "duration_minutes"),
            source_recommendation_id=_activity_value(activity, "source_recommendation_id"),
            rationale=_activity_value(activity, "rationale"),
            url=_activity_value(activity, "url") or "https://example.com/mock-itinerary-activity",
            estimated_cost=_activity_value(activity, "estimated_cost"),
        )
        for activity in activities
    ]
    day_plan = ItineraryDay(
        day=day,
        title=title,
        rationale=rationale,
        activities=normalized_activities,
    )

    return {
        "status": "validated",
        "day": day_plan.model_dump(mode="json"),
    }


@tool(args_schema=FinishItineraryPlanningArgs)
def finish_itinerary_planning(reason: str) -> dict[str, str]:
    """Call this when enough itinerary research and day validation has completed."""
    return {"status": "finished", "reason": reason}


def _activity_value(activity: DayPlanActivityInput | dict, field_name: str):
    """Read activity values from either Pydantic objects or dicts."""
    if isinstance(activity, dict):
        return activity.get(field_name)
    return getattr(activity, field_name)
