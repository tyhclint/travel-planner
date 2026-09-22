"""MCP server exposed to MCP-capable clients such as Claude."""

from datetime import date
import json
from typing import Any, Final

from fastmcp import Client, FastMCP

from app.services.mcp.registry import get_local_registry

mcp = FastMCP("travel_planner_MCP")
KIWI_URL: Final = "https://mcp.kiwi.com"



def _registry():
    from app.services.mcp.registry import get_local_registry

    return get_local_registry()

@mcp.tool()
def list_travel_capabilities() -> str:
    """List the lower-level travel capabilities used by the planner."""
    return json.dumps([tool["name"] for tool in _registry().list_tools()])


@mcp.tool()
async def search_flights(requirements: dict[str, Any], preferences: dict[str, Any]) -> str:
    """Directly search normalized flight options."""
    values = await get_local_registry().call_tool(
        "travel.search_flights",
        {"requirements": requirements, "preferences": preferences},
    )
    return json.dumps(values)

# @mcp.tool()
# async def search_flights(requirements: dict[str, Any], preferences: dict[str, Any]) -> str:
#     """Directly search normalized flight options, using the kiwiMCP. if this fails, connect to KIWI_URL directly."""
#     origin = requirements.get("origin")
#     destination = requirements.get("destination")
#     departure_date = requirements.get("departure_date")
#     if not origin or not destination or not departure_date:
#         raise ValueError("Flight search requires origin, destination, and departure_date")

#     if isinstance(departure_date, str):
#         departure_date = date.fromisoformat(departure_date)
#     kiwi_args: dict[str, Any] = {
#         "flyFrom": origin,
#         "flyTo": destination,
#         "departureDate": departure_date.strftime("%d/%m/%Y"),
#         "adults": requirements.get("travellers", 1),
#         "children": 0,
#         "infants": 0,
#         "cabinClass": {"economy": "M", "premium_economy": "W", "business": "C", "first": "F"}.get(
#             requirements.get("cabin_class", "economy"), "M"
#         ),
#         "currency": requirements.get("currency", "USD").upper(),
#         "locale": requirements.get("locale", "en"),
#     }

#     async with Client(KIWI_URL, timeout=30.0) as kiwi:
#         tools = await kiwi.list_tools()
#         result = await kiwi.call_tool("search-flight", kiwi_args)

#     return json.dumps(result)


@mcp.tool()
async def search_accommodations(
    requirements: dict[str, Any], preferences: dict[str, Any]
) -> str:
    """Directly search normalized accommodation options."""
    values = await _registry().call_tool(
        "travel.search_accommodations",
        {"requirements": requirements, "preferences": preferences},
    )
    return json.dumps(values)


@mcp.tool()
async def search_destination(requirements: dict[str, Any], preferences: dict[str, Any]) -> str:
    """Directly search normalized destination recommendations."""
    values = await _registry().call_tool(
        "travel.search_destination",
        {"requirements": requirements, "preferences": preferences},
    )
    return json.dumps(values)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
