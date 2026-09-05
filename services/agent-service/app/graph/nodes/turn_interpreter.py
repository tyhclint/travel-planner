import re

from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.domain.models.workflow import ChangedField, RequestedCapability, TurnType
from app.graph.state import TravelState


def turn_interpreter_node(state: TravelState):
    latest_input = state.get("latest_user_input") or _latest_human_message(state)
    lowered = latest_input.lower()

    requirements = state.get("trip_requirements") or TripRequirements()
    preferences = state.get("preferences") or TravelPreferences()
    changed_fields: list[ChangedField] = []

    if "cheap" in lowered or "affordable" in lowered:
        preferences = preferences.model_copy(
            update={
                "overall_style": "cheap",
                "flight_style": "cheap",
                "accommodation_style": "cheap",
                "flight_priority": "cheapest",
                "accommodation_priority": "cheapest",
            }
        )
        changed_fields.extend(["budget", "flight_preferences", "accommodation_preferences"])

    if "luxury" in lowered or "luxurious" in lowered:
        preferences = preferences.model_copy(
            update={
                "overall_style": "luxurious",
                "accommodation_style": "luxurious",
                "accommodation_priority": "most_luxurious",
            }
        )
        changed_fields.append("accommodation_preferences")

    destination = _extract_destination(latest_input)
    if destination and destination != requirements.destination:
        requirements = requirements.model_copy(update={"destination": destination})
        changed_fields.append("destination")

    origin = _extract_origin(latest_input)
    if origin and origin != requirements.origin:
        requirements = requirements.model_copy(update={"origin": origin})
        changed_fields.append("origin")

    trip_length_days = _extract_trip_length(lowered)
    if trip_length_days and trip_length_days != requirements.trip_length_days:
        requirements = requirements.model_copy(update={"trip_length_days": trip_length_days})
        changed_fields.append("travel_dates")

    requested_capabilities = _requested_capabilities(lowered)
    missing_required_fields = _missing_required_fields(requested_capabilities, requirements)

    return {
        "latest_user_input": latest_input,
        "turn_type": _infer_turn_type(lowered),
        "requested_capabilities": requested_capabilities,
        "trip_requirements": requirements,
        "preferences": preferences,
        "changed_fields": sorted(set(changed_fields)),
        "missing_required_fields": missing_required_fields,
    }


def _infer_turn_type(text: str) -> TurnType:
    if "plan" in text or "trip" in text:
        return "new_plan"
    return "follow_up_question"


def _latest_human_message(state: TravelState) -> str:
    for message in reversed(state.get("messages", [])):
        if getattr(message, "type", None) == "human":
            return str(message.content)
    return ""


def _requested_capabilities(text: str) -> list[RequestedCapability]:
    capabilities: set[RequestedCapability] = set()

    if any(keyword in text for keyword in ("flight", "flights", "fly")):
        capabilities.add("flight")
    if any(keyword in text for keyword in ("hotel", "accommodation", "stay")):
        capabilities.add("accommodation")
    if any(keyword in text for keyword in ("visit", "places", "recommend", "unique")):
        capabilities.add("destination_research")
    if any(keyword in text for keyword in ("plan", "trip", "itinerary", "day ")):
        capabilities.update({"flight", "accommodation", "destination_research", "itinerary"})

    if not capabilities:
        capabilities.add("destination_research")

    return sorted(capabilities)


def _missing_required_fields(
    capabilities: list[RequestedCapability],
    requirements: TripRequirements,
) -> list[str]:
    missing: list[str] = []

    if (
        any(capability in capabilities for capability in ("flight", "itinerary"))
        and not requirements.origin
    ):
        missing.append("origin")

    if (
        any(
            capability in capabilities
            for capability in ("flight", "accommodation", "destination_research", "itinerary")
        )
        and not requirements.destination
    ):
        missing.append("destination")

    return missing


def _extract_origin(text: str) -> str | None:
    match = re.search(r"\bfrom\s+([A-Za-z\s]+?)\s+to\s+", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip().title()


def _extract_destination(text: str) -> str | None:
    match = re.search(r"\bto\s+([A-Za-z\s]+?)(?:\.|,|$|\s+for|\s+from)", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"\bin\s+([A-Za-z\s]+?)(?:\.|,|$|\s+for|\s+from)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip().title()


def _extract_trip_length(text: str) -> int | None:
    match = re.search(r"\b(\d+)[-\s]?day\b", text)
    if match:
        return int(match.group(1))

    words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
    }
    for word, value in words.items():
        if f"{word}-day" in text or f"{word} day" in text:
            return value
    return None
