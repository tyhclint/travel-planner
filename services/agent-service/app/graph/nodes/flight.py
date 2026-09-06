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
        for item in _flight_items(payload):
            option = _kiwi_item_to_flight_option(item)
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


def _flight_items(payload: Any) -> list[dict[str, Any]]:
    """Find the list of provider flight result items inside common payload shapes."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    result = payload.get("result", payload)
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]

    if not isinstance(result, dict):
        return []

    for key in ("data", "results", "flights", "itineraries"):
        value = result.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return []


def _kiwi_item_to_flight_option(
    item: dict[str, Any],
) -> FlightOption | None:
    """Convert one Kiwi result item into the app's FlightOption model."""
    route = item.get("route") if isinstance(item.get("route"), list) else []
    departure_time = _parse_datetime(
        item.get("local_departure")
        or item.get("utc_departure")
        or _first_route_value(route, "local_departure")
        or _first_route_value(route, "utc_departure")
    )
    arrival_time = _parse_datetime(
        item.get("local_arrival")
        or item.get("utc_arrival")
        or _last_route_value(route, "local_arrival")
        or _last_route_value(route, "utc_arrival")
    )
    if departure_time is None or arrival_time is None:
        return None

    flight_id = item.get("id") or item.get("booking_token") or item.get("deep_link")
    origin = item.get("flyFrom") or _first_route_value(route, "flyFrom")
    destination = item.get("flyTo") or _last_route_value(route, "flyTo")
    price = item.get("price")
    if not flight_id or not origin or not destination or price is None:
        return None

    try:
        return FlightOption(
            id=str(flight_id),
            airline=_airline_name(item, route),
            origin=str(origin),
            destination=str(destination),
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration_minutes=_duration_minutes(item, departure_time, arrival_time),
            stops=_stop_count(item, route),
            cabin_class=_cabin_class(),
            baggage_description=_baggage_description(item),
            total_price=float(price),
            currency=str(item.get("currency") or "USD").upper(),
            provider="kiwi",
            booking_url=item.get("deep_link"),
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
    item: dict[str, Any],
    departure_time: datetime,
    arrival_time: datetime,
) -> int:
    """Resolve itinerary duration in minutes from provider data or timestamps."""
    duration = item.get("duration")
    raw_duration = None
    if isinstance(duration, dict):
        raw_duration = duration.get("total") or duration.get("departure")
    elif isinstance(duration, (int, float)):
        raw_duration = duration

    if raw_duration is not None:
        duration_value = int(raw_duration)
        if duration_value > 72 * 60:
            return max(round(duration_value / 60), 1)
        return max(duration_value, 1)

    return max(round((arrival_time - departure_time).total_seconds() / 60), 1)


def _stop_count(item: dict[str, Any], route: list[Any]) -> int:
    """Resolve the number of stops from explicit provider data or route legs."""
    stops = item.get("stops")
    if isinstance(stops, int):
        return max(stops, 0)

    return max(len(route) - 1, 0)


def _airline_name(item: dict[str, Any], route: list[Any]) -> str:
    """Resolve a display airline name from top-level fields or the first route leg."""
    airline = item.get("airline")
    if isinstance(airline, str) and airline:
        return airline

    airlines = item.get("airlines")
    if isinstance(airlines, list) and airlines:
        return ", ".join(str(value) for value in airlines if value)

    route_airline = _first_route_value(route, "airline")
    if route_airline:
        return str(route_airline)

    return "Unknown airline"


def _cabin_class() -> CabinClass:
    """Return the default cabin class for parsed provider results."""
    return "economy"


def _baggage_description(item: dict[str, Any]) -> str | None:
    """Return a short baggage note when the provider exposes baggage pricing."""
    bags_price = item.get("bags_price")
    if isinstance(bags_price, dict) and bags_price:
        return "Baggage prices available from provider"
    return None


def _first_route_value(route: list[Any], key: str) -> Any:
    """Return the first truthy value for a key across provider route legs."""
    for leg in route:
        if isinstance(leg, dict) and leg.get(key):
            return leg[key]
    return None


def _last_route_value(route: list[Any], key: str) -> Any:
    """Return the last truthy value for a key across provider route legs."""
    for leg in reversed(route):
        if isinstance(leg, dict) and leg.get(key):
            return leg[key]
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
