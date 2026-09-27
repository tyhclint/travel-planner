import json
from datetime import date
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field, ValidationError

from app.services.accommodations.errors import MoodTripPayloadValidationError
from app.services.accommodations.mcp import get_accommodation_mcp_tools
from app.services.accommodations.moodtrip import MoodTripToolOutput


class AccommodationSearchArgs(BaseModel):
    destination: str = Field(..., min_length=1, max_length=100)
    check_in: date
    check_out: date
    adults: int = Field(default=1, ge=1, le=16)
    children: list[int] = Field(default_factory=list, max_length=6)
    rooms: int = Field(default=1, ge=1, le=8)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    country: str | None = Field(default=None, min_length=2, max_length=100)
    max_price: int | None = Field(default=None, ge=0)
    min_rating: float | None = Field(default=None, ge=0, le=5)
    query: str | None = Field(default=None, min_length=1, max_length=500)


class AccommodationDetailsArgs(BaseModel):
    hotel_id: str = Field(..., min_length=1, max_length=200)
    check_in: date | None = None
    check_out: date | None = None
    adults: int = Field(default=1, ge=1, le=16)
    children: list[int] = Field(default_factory=list, max_length=6)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class AccommodationReviewsArgs(BaseModel):
    hotel_id: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(default=10, ge=1, le=50)
    language: str | None = Field(default=None, min_length=2, max_length=10)


class FinishAccommodationSearchArgs(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


def _format_moodtrip_date(value: date) -> str:
    """Format a Python date using the ISO date format expected by MoodTrip."""
    return value.isoformat()


def _extract_moodtrip_payload(raw_result: Any) -> Any:
    """Extract structured payload data from possible LangChain tool result shapes."""
    if isinstance(raw_result, ToolMessage):
        if raw_result.artifact:
            return raw_result.artifact.get("structured_content", raw_result.artifact)
        return _json_payload(raw_result.content)

    if isinstance(raw_result, tuple) and len(raw_result) == 2:
        content, artifact = raw_result
        if isinstance(artifact, dict):
            return artifact.get("structured_content", artifact)
        return _json_payload(content)

    return _json_payload(raw_result)


def _json_payload(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


async def _get_moodtrip_tool(tool_name: str) -> BaseTool:
    """Load MoodTrip MCP tools and return the requested provider tool."""
    tools = await get_accommodation_mcp_tools()
    expected_names = {tool_name, f"moodtrip_{tool_name}"}
    for mcp_tool in tools:
        if mcp_tool.name in expected_names:
            return mcp_tool

    available_tool_names = ", ".join(tool.name for tool in tools)
    raise RuntimeError(
        f"MoodTrip tool {tool_name} not found. Available tools: {available_tool_names}"
    )


def _validate_moodtrip_payload(payload: Any, *, tool_name: str) -> dict[str, Any]:
    try:
        return MoodTripToolOutput.model_validate(payload).model_dump()
    except ValidationError as exc:
        raise MoodTripPayloadValidationError(
            f"MoodTrip {tool_name} returned a payload that is not a JSON object."
        ) from exc


@tool(args_schema=AccommodationSearchArgs)
async def search_accommodations(
    destination: str,
    check_in: date,
    check_out: date,
    adults: int = 1,
    children: list[int] | None = None,
    rooms: int = 1,
    currency: str = "USD",
    country: str | None = None,
    max_price: int | None = None,
    min_rating: float | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    """Search real accommodation rates using MoodTrip through its MCP server."""
    moodtrip_tool = await _get_moodtrip_tool("searchHotelsWithRates")
    search_query = query or f"Hotels in {destination}"

    moodtrip_args: dict[str, Any] = {
        "query": search_query,
        "city": destination,
        "checkIn": _format_moodtrip_date(check_in),
        "checkOut": _format_moodtrip_date(check_out),
        "adults": adults,
        "children": children or [],
        "rooms": rooms,
        "currency": currency.upper(),
    }
    if country is not None:
        moodtrip_args["country"] = country
    if max_price is not None:
        moodtrip_args["maxPrice"] = max_price
    if min_rating is not None:
        moodtrip_args["minRating"] = min_rating

    raw_result = await moodtrip_tool.ainvoke(moodtrip_args)
    payload = _extract_moodtrip_payload(raw_result)
    return {
        "provider": "moodtrip",
        "tool": "searchHotelsWithRates",
        "result": _validate_moodtrip_payload(payload, tool_name="searchHotelsWithRates"),
    }


@tool(args_schema=AccommodationDetailsArgs)
async def get_accommodation_details(
    hotel_id: str,
    check_in: date | None = None,
    check_out: date | None = None,
    adults: int = 1,
    children: list[int] | None = None,
    currency: str = "USD",
) -> dict[str, Any]:
    """Fetch detailed hotel data using MoodTrip through its MCP server."""
    moodtrip_tool = await _get_moodtrip_tool("getHotelDetails")

    moodtrip_args: dict[str, Any] = {
        "hotelId": hotel_id,
        "adults": adults,
        "children": children or [],
        "currency": currency.upper(),
    }
    if check_in is not None:
        moodtrip_args["checkin"] = _format_moodtrip_date(check_in)
    if check_out is not None:
        moodtrip_args["checkout"] = _format_moodtrip_date(check_out)

    raw_result = await moodtrip_tool.ainvoke(moodtrip_args)
    payload = _extract_moodtrip_payload(raw_result)
    return {
        "provider": "moodtrip",
        "tool": "getHotelDetails",
        "hotel_id": hotel_id,
        "result": _validate_moodtrip_payload(payload, tool_name="getHotelDetails"),
    }


@tool(args_schema=AccommodationReviewsArgs)
async def get_accommodation_reviews(
    hotel_id: str,
    limit: int = 10,
    language: str | None = None,
) -> dict[str, Any]:
    """Fetch hotel reviews using MoodTrip through its MCP server."""
    moodtrip_tool = await _get_moodtrip_tool("getHotelReviews")

    moodtrip_args: dict[str, Any] = {
        "hotelId": hotel_id,
        "limit": limit,
    }
    if language is not None:
        moodtrip_args["language"] = language

    raw_result = await moodtrip_tool.ainvoke(moodtrip_args)
    payload = _extract_moodtrip_payload(raw_result)
    return {
        "provider": "moodtrip",
        "tool": "getHotelReviews",
        "hotel_id": hotel_id,
        "result": _validate_moodtrip_payload(payload, tool_name="getHotelReviews"),
    }


@tool(args_schema=FinishAccommodationSearchArgs)
def finish_accommodation_search(reason: str) -> dict[str, str]:
    """Call this when enough accommodation data has been gathered for ranking."""
    return {"status": "finished", "reason": reason}
