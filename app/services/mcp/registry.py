"""Small JSON-only tool registry used by the standalone MCP test server."""

from collections.abc import Callable, Mapping
from datetime import date
from functools import lru_cache
from typing import Any, Awaitable
from typing import Final

from fastmcp import Client
from pydantic import ValidationError

from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.services.search.rag import MarkdownRAGSearchService

ToolHandler = Callable[[dict[str, Any]], list[dict[str, Any]] | Awaitable[list[dict[str, Any]]]]
KIWI_MCP_SERVER_NAME: Final = "kiwi"
KIWI_MCP_DEFAULT_URL: Final = "https://mcp.kiwi.com"




class MCPToolRegistry:
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

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            _, handler = self._handlers[name]
        except KeyError as exc:
            raise ValueError(f"Unknown MCP tool: {name}") from exc
        result = handler(arguments)
        if hasattr(result, "__await__"):
            return await result
        return result


def _requirements(arguments: dict[str, Any]) -> dict[str, Any]:
    return arguments.get("requirements", {})


def _json_safe(value: Any) -> Any:
    """Convert MCP/Pydantic response objects into JSON-serializable values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json", by_alias=True))
    if hasattr(value, "structuredContent"):
        return _json_safe(value.structuredContent)
    if hasattr(value, "structured_content"):
        return _json_safe(value.structured_content)
    raise TypeError(f"Unsupported MCP result type: {type(value).__name__}")


async def _search_flights(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = _requirements(arguments)
    origin = requirements.get("origin")
    destination = requirements.get("destination")
    departure_date = requirements.get("departure_date")
    if not origin or not destination or not departure_date:
        raise ValueError("Flight search requires origin, destination, and departure_date")

    if isinstance(departure_date, str):
        departure_date = date.fromisoformat(departure_date)
    kiwi_args: dict[str, Any] = {
        "flyFrom": origin,
        "flyTo": destination,
        "departureDate": departure_date.strftime("%d/%m/%Y"),
        "adults": requirements.get("travellers", 1),
        "children": 0,
        "infants": 0,
        "cabinClass": {"economy": "M", "premium_economy": "W", "business": "C", "first": "F"}.get(
            requirements.get("cabin_class", "economy"), "M"
        ),
        "currency": requirements.get("currency", "USD").upper(),
        "locale": requirements.get("locale", "en"),
    }
    optional_fields = {
        "departure_date_flex_days": "departureDateFlexDays",
        "departure_date_to": "departureDateTo",
        "return_date_flex_days": "returnDateFlexDays",
        "return_date_to": "returnDateTo",
        "max_stops": "max_sector_stopovers",
        "price_from": "price_from",
        "price_to": "price_to",
    }
    for requirement_name, kiwi_name in optional_fields.items():
        value = requirements.get(requirement_name)
        if value is not None:
            if requirement_name.endswith("_to") and isinstance(value, str):
                value = date.fromisoformat(value).strftime("%d/%m/%Y")
            kiwi_args[kiwi_name] = value

    if requirements.get("return_date"):
        return_date = requirements["return_date"]
        if isinstance(return_date, str):
            return_date = date.fromisoformat(return_date)
        kiwi_args["returnDate"] = return_date.strftime("%d/%m/%Y")

    async with Client(KIWI_MCP_DEFAULT_URL, timeout=30.0) as kiwi:
        tools = await kiwi.list_tools()
        flight_tool = next(
            (tool for tool in tools if tool.name in {"search-flight", "kiwi_search-flight"}),
            None,
        )
        if flight_tool is None:
            available = ", ".join(tool.name for tool in tools)
            raise RuntimeError(f"Kiwi flight search tool not found. Available tools: {available}")

        result = await kiwi.call_tool(flight_tool.name, kiwi_args)
        payload = _json_safe(result)
        if not isinstance(payload, dict):
            raise RuntimeError("Kiwi search-flight returned a non-object payload")
        return [{"provider": "kiwi", "result": payload}]

def _search_accommodations(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = _requirements(arguments)
    destination = requirements.get("destination") or "Tokyo"
    currency = requirements.get("currency") or "USD"
    return [
        {
            "id": "mock-stay-1",
            "name": f"{destination} Central Rooms",
            "location": f"Central {destination}",
            "nightly_price": 120,
            "total_price": 480,
            "currency": currency,
            "amenities": ["wifi", "transit nearby"],
            "provider": "mock",
        }
    ]


def _search_destination(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        requirements = TripRequirements.model_validate(arguments.get("requirements", {}))
        preferences = TravelPreferences.model_validate(arguments.get("preferences", {}))
    except ValidationError as exc:
        raise ValueError(f"Invalid destination search arguments: {exc}") from exc

    values = MarkdownRAGSearchService().search_destination(requirements, preferences)
    return [_json_safe(value) for value in values]


def _register_default_tools(registry: MCPToolRegistry) -> None:
    registry.register("travel.search_flights", "Search available flights.", _search_flights)
    registry.register(
        "travel.search_accommodations",
        "Search accommodation options.",
        _search_accommodations,
    )
    registry.register(
        "travel.search_destination",
        "Find destination recommendations from local guides.",
        _search_destination,
    )


@lru_cache
def get_local_registry() -> MCPToolRegistry:
    registry = MCPToolRegistry()
    _register_default_tools(registry)
    return registry
