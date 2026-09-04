from datetime import date
from typing import Any, Literal

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.services.flights.mcp import get_flight_mcp_tools

CabinClassInput = Literal["economy", "premium_economy", "business", "first"]
FlightSortInput = Literal["price", "duration", "quality", "date", "popularity"]

CABIN_CLASS_TO_KIWI: dict[CabinClassInput, str] = {
    "economy": "M",
    "premium_economy": "W",
    "business": "C",
    "first": "F",
}


class FlightSearchArgs(BaseModel):
    fly_from: str = Field(..., min_length=1, max_length=100)
    fly_to: str = Field(..., min_length=1, max_length=100)
    departure_date: date
    return_date: date | None = None
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=8)
    infants: int = Field(default=0, ge=0, le=4)
    cabin_class: CabinClassInput = "economy"
    currency: str = Field(default="USD", min_length=3, max_length=3)
    sort: FlightSortInput = "price"
    max_stops: int | None = Field(default=None, ge=0)
    price_to: int | None = Field(default=None, ge=0)


def _format_kiwi_date(value: date) -> str:
    """Format a Python date using the dd/mm/yyyy format expected by Kiwi."""
    return value.strftime("%d/%m/%Y")


def _extract_kiwi_payload(raw_result: Any) -> Any:
    """Extract structured payload data from possible LangChain tool result shapes."""
    if isinstance(raw_result, ToolMessage):
        if raw_result.artifact:
            return raw_result.artifact.get("structured_content", raw_result.artifact)
        return raw_result.content

    if isinstance(raw_result, tuple) and len(raw_result) == 2:
        content, artifact = raw_result
        if isinstance(artifact, dict):
            return artifact.get("structured_content", artifact)
        return content

    return raw_result


async def _get_kiwi_search_flight_tool() -> BaseTool:
    """Load the Kiwi MCP tools and return only the flight search tool."""
    tools = await get_flight_mcp_tools()
    for mcp_tool in tools:
        if mcp_tool.name == "kiwi_search-flight":
            return mcp_tool

    available_tool_names = ", ".join(tool.name for tool in tools)
    raise RuntimeError(f"Kiwi flight search tool not found. Available tools: {available_tool_names}")


@tool(args_schema=FlightSearchArgs)
async def search_flights(
    fly_from: str,
    fly_to: str,
    departure_date: date,
    return_date: date | None = None,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    cabin_class: CabinClassInput = "economy",
    currency: str = "USD",
    sort: FlightSortInput = "price",
    max_stops: int | None = None,
    price_to: int | None = None,
) -> dict[str, Any]:
    """Search real flight itineraries using Kiwi.com through the Kiwi MCP server."""
    kiwi_tool = await _get_kiwi_search_flight_tool()

    kiwi_args = {
        "flyFrom": fly_from,
        "flyTo": fly_to,
        "departureDate": _format_kiwi_date(departure_date),
        "adults": adults,
        "children": children,
        "infants": infants,
        "cabinClass": CABIN_CLASS_TO_KIWI[cabin_class],
        "currency": currency.upper(),
        "sort": sort,
    }

    if return_date is not None:
        kiwi_args["returnDate"] = _format_kiwi_date(return_date)
    if max_stops is not None:
        kiwi_args["max_sector_stopovers"] = max_stops
    if price_to is not None:
        kiwi_args["price_to"] = price_to

    raw_result = await kiwi_tool.ainvoke(kiwi_args)
    return {"provider": "kiwi", "result": _extract_kiwi_payload(raw_result)}
