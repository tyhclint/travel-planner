import json
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from pydantic import ValidationError

from app.core.llm import get_flight_llm
from app.domain.models.errors import AgentError
from app.domain.models.flights import CabinClass, FlightOption
from app.graph.state import TravelState
from app.prompts.flight import FLIGHT_AGENT_SYSTEM_PROMPT, FLIGHT_AGENT_USER_PROMPT
from app.services.flights.kiwi import KiwiItineraryDict, KiwiLegDict
from app.services.flights.tools import finish_flight_search, search_flights

MIN_USABLE_FLIGHT_OPTIONS = 3
MAX_FLIGHT_SEARCH_ATTEMPTS = 3
FLIGHT_TOOL_NAMES = {"search_flights", "finish_flight_search"}


def flight_node(state: TravelState):
    """Run the flight ReAct loop and populate flight_results after a terminal action."""
    messages = state.get("messages", [])
    search_tool_messages = _tool_messages(messages, "search_flights")
    parsed_options = _parse_flight_tool_messages(messages)

    if _last_tool_message_name(messages) == "finish_flight_search":
        return _finalize_flight_results(parsed_options)

    if len(search_tool_messages) >= MAX_FLIGHT_SEARCH_ATTEMPTS:
        return _finalize_flight_results(parsed_options)

    try:
        llm = get_flight_llm().bind_tools([search_flights, finish_flight_search])
        response = llm.invoke(
            _flight_prompt_messages(
                state=state,
                search_attempts=len(search_tool_messages),
                parsed_options=parsed_options,
            )
        )
    except RuntimeError as exc:
        return _flight_failed_update(
            "llm_action_failed",
            f"Flight agent could not choose the next flight action: {exc}",
            retryable=True,
        )

    tool_calls = _known_tool_calls(getattr(response, "tool_calls", []) or [])
    if len(tool_calls) != 1:
        return _flight_failed_update(
            "invalid_llm_action",
            "Flight agent must call exactly one flight tool.",
            retryable=True,
            messages=[response],
        )

    return {
        "messages": [response],
        "task_status": {"flight": "running"},
    }


def route_flight_agent(state: TravelState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "fan_in"

    tool_calls = getattr(messages[-1], "tool_calls", []) or []
    if _known_tool_calls(tool_calls):
        return "flight_tools"

    return "fan_in"


def _flight_prompt_messages(
    state: TravelState,
    search_attempts: int,
    parsed_options: list[FlightOption],
):
    """Build the flight agent prompt from structured state and prior flight tool history."""
    return [
        SystemMessage(
            content=FLIGHT_AGENT_SYSTEM_PROMPT.format(
                min_flight_options=MIN_USABLE_FLIGHT_OPTIONS,
                max_search_attempts=MAX_FLIGHT_SEARCH_ATTEMPTS,
            )
        ),
        HumanMessage(
            content=FLIGHT_AGENT_USER_PROMPT.format(
                conversation_summary=state.get("conversation_summary", ""),
                latest_user_input=state.get("latest_user_input", ""),
                trip_requirements=_json_value(state.get("trip_requirements")),
                preferences=_json_value(state.get("preferences")),
                flight_task_status=state.get("task_status", {}).get("flight"),
                search_attempts=search_attempts,
                usable_options=_json_value(parsed_options),
                errors=_json_value(state.get("errors", [])),
            )
        ),
        *_flight_agent_history(state.get("messages", [])),
    ]


def _flight_agent_history(messages: list[Any]) -> list[Any]:
    """Keep prior flight AI/tool messages in order so tool-call IDs stay paired."""
    history: list[Any] = []
    for message in messages:
        if _known_tool_calls(getattr(message, "tool_calls", []) or []) or (
            isinstance(message, ToolMessage) and message.name in FLIGHT_TOOL_NAMES
        ):
            history.append(message)
    return history


def _known_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only tool calls that belong to this flight agent loop."""
    return [call for call in tool_calls if call.get("name") in FLIGHT_TOOL_NAMES]


def _tool_messages(messages: list[Any], name: str) -> list[ToolMessage]:
    """Filter graph messages down to ToolMessages with the requested tool name."""
    return [
        message
        for message in messages
        if isinstance(message, ToolMessage) and message.name == name
    ]


def _last_tool_message_name(messages: list[Any]) -> str | None:
    """Return the name of the latest message when it is a ToolMessage."""
    if messages and isinstance(messages[-1], ToolMessage):
        return messages[-1].name
    return None


def _finalize_flight_results(options: list[FlightOption]):
    """Create the final state update once flight search has reached a terminal action."""
    if options:
        return {
            "flight_results": options,
            "task_status": {"flight": "completed"},
        }

    return _flight_failed_update(
        "no_usable_flights",
        "Flight search completed but no usable flight options could be parsed.",
        retryable=True,
    )


def _flight_failed_update(
    error_type: str,
    message: str,
    *,
    retryable: bool,
    messages: list[Any] | None = None,
):
    """Build a failed flight-task update with a normalized AgentError."""
    update = {
        "task_status": {"flight": "failed"},
        "errors": [
            AgentError(
                source="flight",
                error_type=error_type,
                message=message,
                retryable=retryable,
            )
        ],
    }
    if messages:
        update["messages"] = messages
    return update


def _parse_flight_tool_messages(messages: list[Any]) -> list[FlightOption]:
    """Parse all flight-search ToolMessages into deduplicated FlightOption objects."""
    options: list[FlightOption] = []
    seen_ids: set[str] = set()

    for message in _tool_messages(messages, "search_flights"):
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


def _json_value(value: Any) -> str:
    """Serialize prompt values to JSON, including Pydantic models."""
    if value is None:
        return "null"
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json()
    if isinstance(value, list):
        return json.dumps([_json_safe(item) for item in value], default=str)
    return json.dumps(_json_safe(value), default=str)


def _json_safe(value: Any) -> Any:
    """Convert Pydantic values into structures json.dumps can handle."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value
