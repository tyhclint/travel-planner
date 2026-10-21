"""MCP-shaped tool boundary for travel capabilities."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

from pydantic import ValidationError

from app.domain.models.accommodations import AccommodationOption
from app.domain.models.flights import FlightOption
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.services.search.rag import MarkdownRAGSearchService

ToolHandler = Callable[[dict[str, Any]], list[dict[str, Any]]]


class MCPToolRegistry:
    """Register and invoke typed travel tools using MCP-style names."""

    def __init__(self) -> None:
        self._handlers: dict[str, tuple[dict[str, Any], ToolHandler]] = {}

    def register(self, name: str, description: str, handler: ToolHandler) -> None:
        self._handlers[name] = (
            {
                "name": name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirements": {"type": "object"},
                        "preferences": {"type": "object"},
                    },
                    "required": ["requirements", "preferences"],
                },
            },
            handler,
        )

    def list_tools(self) -> list[dict[str, Any]]:
        return [schema for schema, _ in self._handlers.values()]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            _, handler = self._handlers[name]
        except KeyError as exc:
            raise ValueError(f"Unknown MCP tool: {name}") from exc
        return handler(arguments)


def _requirements(value: dict[str, Any]) -> TripRequirements:
    return TripRequirements.model_validate(value)


def _preferences(value: dict[str, Any]) -> TravelPreferences:
    return TravelPreferences.model_validate(value)


def _search_flights(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = _requirements(arguments.get("requirements", {}))
    preferences = _preferences(arguments.get("preferences", {}))

    origin = requirements.origin or "SIN"
    destination = requirements.destination or "Tokyo"
    departure_date = requirements.departure_date or datetime.now(timezone.utc).date()
    departure_time = datetime.combine(
        departure_date,
        datetime.min.time(),
        tzinfo=timezone.utc,
    ) + timedelta(hours=8)

    style_multiplier = {
        "cheap": 0.85,
        "standard": 1.0,
        "luxurious": 1.35,
    }[preferences.flight_style]
    baseline = max(180.0, float(requirements.budget or 480.0) / max(requirements.travellers, 1))

    options = [
        FlightOption(
            id=f"{origin}-{destination}-direct",
            airline="Demo Air",
            origin=origin,
            destination=destination,
            departure_time=departure_time,
            arrival_time=departure_time + timedelta(hours=6, minutes=20),
            duration_minutes=380,
            stops=0,
            cabin_class="economy",
            baggage_description="1 carry-on included",
            total_price=round(baseline * style_multiplier, 2),
            currency=requirements.currency,
            provider="local-mock",
        ),
        FlightOption(
            id=f"{origin}-{destination}-one-stop",
            airline="Budget Connect",
            origin=origin,
            destination=destination,
            departure_time=departure_time + timedelta(hours=3),
            arrival_time=departure_time + timedelta(hours=11, minutes=15),
            duration_minutes=495,
            stops=1,
            cabin_class="economy",
            baggage_description="Carry-on only",
            total_price=round(baseline * 0.72, 2),
            currency=requirements.currency,
            provider="local-mock",
        ),
    ]
    return [option.model_dump(mode="json") for option in options]


def _search_accommodations(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = _requirements(arguments.get("requirements", {}))
    preferences = _preferences(arguments.get("preferences", {}))

    destination = requirements.destination or "Tokyo"
    check_in = requirements.departure_date
    check_out = requirements.return_date
    nightly_baseline = {
        "cheap": 75.0,
        "standard": 140.0,
        "luxurious": 320.0,
    }[preferences.accommodation_style]
    nights = requirements.trip_length_days or (
        (check_out - check_in).days if check_in and check_out else 3
    )
    nights = max(nights, 1)

    options = [
        AccommodationOption(
            id=f"{destination.lower()}-central-stay",
            name=f"{destination} Central Stay",
            location=destination,
            check_in=check_in,
            check_out=check_out,
            rating=4.3,
            nightly_price=nightly_baseline,
            total_price=round(nightly_baseline * nights, 2),
            currency=requirements.currency,
            amenities=["wifi", "train access", "breakfast"],
            provider="local-mock",
        ),
        AccommodationOption(
            id=f"{destination.lower()}-budget-inn",
            name=f"{destination} Budget Inn",
            location=destination,
            check_in=check_in,
            check_out=check_out,
            rating=4.0,
            nightly_price=round(nightly_baseline * 0.68, 2),
            total_price=round(nightly_baseline * 0.68 * nights, 2),
            currency=requirements.currency,
            amenities=["wifi"],
            provider="local-mock",
        ),
    ]
    return [option.model_dump(mode="json") for option in options]


def _search_destination(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        requirements = _requirements(arguments.get("requirements", {}))
        preferences = _preferences(arguments.get("preferences", {}))
    except ValidationError as exc:
        raise ValueError(f"Invalid destination search arguments: {exc}") from exc

    values = MarkdownRAGSearchService().search_destination(requirements, preferences)
    return [value.model_dump(mode="json") for value in values]


def _register_default_tools(registry: MCPToolRegistry) -> None:
    registry.register(
        "travel.search_flights",
        "Search and normalize available flights for a trip.",
        _search_flights,
    )
    registry.register(
        "travel.search_accommodations",
        "Search and normalize accommodation options for a trip.",
        _search_accommodations,
    )
    registry.register(
        "travel.search_destination",
        "Find destination recommendations for a trip.",
        _search_destination,
    )


@lru_cache
def get_local_registry() -> MCPToolRegistry:
    registry = MCPToolRegistry()
    _register_default_tools(registry)
    return registry
