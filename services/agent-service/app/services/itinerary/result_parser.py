import json
from typing import Any

from langchain_core.messages import ToolMessage
from pydantic import ValidationError

from app.domain.models.itinerary import ItineraryDay
from app.domain.models.recommendations import DestinationRecommendation


def parse_destination_research_tool_messages(
    research_tool_messages: list[ToolMessage],
) -> list[DestinationRecommendation]:
    """Parse destination research ToolMessages into deduplicated recommendations."""
    recommendations: list[DestinationRecommendation] = []
    seen: set[tuple[str, str]] = set()

    for message in research_tool_messages:
        payload = _json_payload(message.content)
        for value in payload.get("recommendations", []):
            try:
                recommendation = DestinationRecommendation.model_validate(value)
            except ValidationError:
                continue

            key = (
                recommendation.name.strip().lower(),
                (recommendation.source_url or "").strip().lower(),
            )
            if key in seen:
                continue

            seen.add(key)
            recommendations.append(recommendation)

    return recommendations


def parse_validated_day_plan_tool_messages(
    validation_tool_messages: list[ToolMessage],
) -> list[ItineraryDay]:
    """Parse validate_day_plan ToolMessages into sorted, deduplicated itinerary days."""
    days_by_number: dict[int, ItineraryDay] = {}

    for message in validation_tool_messages:
        payload = _json_payload(message.content)
        if payload.get("status") != "validated":
            continue

        try:
            day = ItineraryDay.model_validate(payload.get("day"))
        except ValidationError:
            continue

        days_by_number[day.day] = day

    return [days_by_number[day_number] for day_number in sorted(days_by_number)]


def _json_payload(content: Any) -> dict[str, Any]:
    """Return a dictionary payload from LangChain ToolMessage content."""
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            loaded = json.loads(content)
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}
    return {}
