import json
from datetime import datetime
from typing import Any

from langchain_core.messages import ToolMessage
from pydantic import ValidationError

from app.domain.models.flights import CabinClass, FlightOption
from app.services.flights.kiwi import KiwiItineraryDict, KiwiLegDict


def parse_flight_tool_messages(search_tool_messages: list[ToolMessage]) -> list[FlightOption]:
    """Parse flight-search ToolMessages into deduplicated FlightOption objects."""
    options: list[FlightOption] = []
    seen_ids: set[str] = set()

    for message in search_tool_messages:
        payload = _load_tool_payload(message)
        if not isinstance(payload, dict):
            continue

        result = payload.get("result", {})
        if not isinstance(result, dict):
            continue

        currency = str(result.get("currency") or "USD").upper()
        itineraries = result.get("itineraries", [])
        if not isinstance(itineraries, list):
            continue

        for itinerary in itineraries:
            option = _kiwi_itinerary_to_flight_option(itinerary, currency)
            if option is None or option.id in seen_ids:
                continue
            options.append(option)
            seen_ids.add(option.id)

    return options


def _load_tool_payload(message: ToolMessage) -> Any:
    """Extract structured payload data from a LangChain ToolMessage."""
    artifact = getattr(message, "artifact", None)
    if artifact:
        return artifact.get("structured_content", artifact)

    if isinstance(message.content, str):
        try:
            return json.loads(message.content)
        except json.JSONDecodeError:
            return {}

    return message.content


def _kiwi_itinerary_to_flight_option(
    itinerary: KiwiItineraryDict,
    currency: str,
) -> FlightOption | None:
    """Convert one validated Kiwi itinerary into the app's FlightOption model."""
    outbound = itinerary.get("outbound")
    if not isinstance(outbound, dict):
        return None

    route = outbound.get("route") if isinstance(outbound.get("route"), list) else []
    departure_time = _parse_datetime(outbound.get("departureTime"))
    arrival_time = _parse_datetime(outbound.get("arrivalTime"))
    if departure_time is None or arrival_time is None:
        return None

    flight_id = itinerary.get("id") or itinerary.get("bookingUrl")
    origin = outbound.get("from") or _route_endpoint(route, first=True)
    destination = outbound.get("to") or _route_endpoint(route, first=False)
    price = itinerary.get("price")
    if not flight_id or not origin or not destination or price is None:
        return None

    try:
        return FlightOption(
            id=str(flight_id),
            airline=_airline_name(itinerary, outbound),
            origin=str(origin),
            destination=str(destination),
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration_minutes=_duration_minutes(
                itinerary,
                outbound,
                departure_time,
                arrival_time,
            ),
            stops=_stop_count(outbound),
            cabin_class=_cabin_class(outbound),
            baggage_description=_baggage_description(itinerary),
            total_price=float(price),
            currency=currency,
            provider="kiwi",
            booking_url=itinerary.get("bookingUrl"),
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse provider datetime values and return None for unsupported formats."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _duration_minutes(
    itinerary: KiwiItineraryDict,
    outbound: KiwiLegDict,
    departure_time: datetime,
    arrival_time: datetime,
) -> int:
    """Resolve itinerary duration in minutes from Kiwi seconds or timestamps."""
    raw_duration = itinerary.get("totalDurationSeconds") or outbound.get("durationSeconds")
    if raw_duration is not None:
        return max(round(int(raw_duration) / 60), 1)

    return max(round((arrival_time - departure_time).total_seconds() / 60), 1)


def _stop_count(outbound: KiwiLegDict) -> int:
    """Resolve the outbound stop count from Kiwi leg data."""
    stops = outbound.get("stops")
    if isinstance(stops, int):
        return max(stops, 0)

    route = outbound.get("route") if isinstance(outbound.get("route"), list) else []
    return max(len(route) - 1, 0)


def _airline_name(itinerary: KiwiItineraryDict, outbound: KiwiLegDict) -> str:
    """Resolve a display airline name from the first Kiwi segment."""
    segments = outbound.get("segments")
    if isinstance(segments, list):
        names = [
            str(segment.get("carrierName") or segment.get("carrier"))
            for segment in segments
            if isinstance(segment, dict) and (segment.get("carrierName") or segment.get("carrier"))
        ]
        if names:
            return ", ".join(dict.fromkeys(names))

    itinerary_id = itinerary.get("id")
    if itinerary_id:
        return f"Kiwi itinerary {itinerary_id}"

    return "Unknown airline"


def _cabin_class(outbound: KiwiLegDict) -> CabinClass:
    """Normalize Kiwi cabin class labels into the app's CabinClass literals."""
    cabin_class = outbound.get("cabinClass")
    if not isinstance(cabin_class, str):
        return "economy"

    normalized = cabin_class.lower().replace(" ", "_")
    if normalized in ("economy", "premium_economy", "business", "first"):
        return normalized

    return "economy"


def _baggage_description(item: KiwiItineraryDict) -> str | None:
    """Return a short baggage note from Kiwi included baggage counts."""
    baggage = item.get("baggage")
    if isinstance(baggage, dict):
        personal = int(baggage.get("personalItem") or 0)
        cabin = int(baggage.get("cabinBag") or 0)
        checked = int(baggage.get("checkedBag") or 0)
        return (
            f"Included bags: personal item x{personal}, "
            f"cabin bag x{cabin}, checked bag x{checked}"
        )
    return None


def _route_endpoint(route: list[Any], *, first: bool) -> Any:
    """Return the first or last airport code from a Kiwi route list."""
    if not route:
        return None
    value = route[0] if first else route[-1]
    if value:
        return value
    return None
