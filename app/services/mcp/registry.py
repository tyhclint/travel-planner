"""MCP-shaped tool boundary for travel provider capabilities."""

from collections.abc import Callable
from functools import lru_cache
from typing import Any

from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.services.accommodations.mock import MockAccommodationService
from app.services.flights.mock import MockFlightService
from app.services.search.mock import MockSearchService

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


def _register_default_tools(registry: MCPToolRegistry) -> None:
    flight_service = MockFlightService()
    accommodation_service = MockAccommodationService()
    search_service = MockSearchService()

    registry.register(
        "travel.search_flights",
        "Search and normalize available flights for a trip.",
        lambda args: [option.model_dump(mode="json") for option in flight_service.search_flights(_requirements(args["requirements"]), _preferences(args["preferences"]))],
    )
    registry.register(
        "travel.search_accommodations",
        "Search and normalize accommodation options for a trip.",
        lambda args: [option.model_dump(mode="json") for option in accommodation_service.search_accommodations(_requirements(args["requirements"]), _preferences(args["preferences"]))],
    )
    registry.register(
        "travel.search_destination",
        "Find destination recommendations for a trip.",
        lambda args: [option.model_dump(mode="json") for option in search_service.search_destination(_requirements(args["requirements"]), _preferences(args["preferences"]))],
    )


@lru_cache
def get_local_registry() -> MCPToolRegistry:
    registry = MCPToolRegistry()
    _register_default_tools(registry)
    return registry
