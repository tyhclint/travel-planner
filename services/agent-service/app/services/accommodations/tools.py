import json
from datetime import date
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.services.accommodations.errors import MoodTripPayloadValidationError
from app.services.accommodations.mcp import get_accommodation_mcp_tools
from app.services.accommodations.moodtrip import (
    MoodTripHotelReviewsOutput,
    MoodTripHotelDetailsOutput,
    MoodTripSearchHotelsWithRatesOutput,
    MoodTripToolOutput,
)


class MoodTripRoomOccupancyArgs(BaseModel):
    adults: int = Field(..., ge=1, le=16)
    children: list[int] = Field(default_factory=list, max_length=6)


class MoodTripSearchHotelsWithRatesArgs(BaseModel):
    city_name: str | None = Field(default=None, min_length=1, max_length=100)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    place_id: str | None = Field(default=None, min_length=1, max_length=200)
    checkin: date
    checkout: date
    occupancies: list[MoodTripRoomOccupancyArgs] = Field(..., min_length=1, max_length=8)
    hotel_name: str | None = Field(default=None, min_length=1, max_length=200)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    guest_nationality: str | None = Field(default=None, min_length=2, max_length=2)
    max_price: float | None = Field(default=None, ge=0)
    limit: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_location(self):
        has_place = bool(self.place_id)
        has_city_country = bool(self.city_name and self.country_code)
        if not has_place and not has_city_country:
            raise ValueError("Provide either place_id or both city_name and country_code.")
        return self


class MoodTripHotelDetailsArgs(BaseModel):
    hotel_id: str = Field(..., min_length=1, max_length=200)
    check_in: date | None = None
    check_out: date | None = None
    adults: int = Field(default=1, ge=1, le=16)
    children: list[int] = Field(default_factory=list, max_length=6)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class MoodTripHotelReviewsArgs(BaseModel):
    hotel_id: str = Field(..., min_length=1, max_length=200)
    get_sentiment: bool = False


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


def _validate_moodtrip_payload(payload: Any, *, tool_name: str, output_model) -> Any:
    try:
        return output_model.model_validate(payload).model_dump(mode="json")
    except ValidationError as exc:
        raise MoodTripPayloadValidationError(
            f"MoodTrip {tool_name} returned a payload that does not match its output schema."
        ) from exc


@tool(args_schema=MoodTripSearchHotelsWithRatesArgs)
async def search_accommodations(
    checkin: date,
    checkout: date,
    occupancies: list[MoodTripRoomOccupancyArgs],
    city_name: str | None = None,
    country_code: str | None = None,
    place_id: str | None = None,
    hotel_name: str | None = None,
    currency: str = "USD",
    guest_nationality: str | None = None,
    max_price: float | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search real accommodation rates using MoodTrip through its MCP server."""
    moodtrip_tool = await _get_moodtrip_tool("searchHotelsWithRates")

    moodtrip_args: dict[str, Any] = {
        "checkin": _format_moodtrip_date(checkin),
        "checkout": _format_moodtrip_date(checkout),
        "occupancies": [
            occupancy.model_dump() if hasattr(occupancy, "model_dump") else occupancy
            for occupancy in occupancies
        ],
        "currency": currency.upper(),
    }
    if city_name is not None:
        moodtrip_args["cityName"] = city_name
    if country_code is not None:
        moodtrip_args["countryCode"] = country_code.upper()
    if place_id is not None:
        moodtrip_args["placeId"] = place_id
    if hotel_name is not None:
        moodtrip_args["hotelName"] = hotel_name
    if guest_nationality is not None:
        moodtrip_args["guestNationality"] = guest_nationality.upper()
    if max_price is not None:
        moodtrip_args["maxPrice"] = max_price
    if limit is not None:
        moodtrip_args["limit"] = limit

    raw_result = await moodtrip_tool.ainvoke(moodtrip_args)
    payload = _extract_moodtrip_payload(raw_result)
    return {
        "provider": "moodtrip",
        "tool": "searchHotelsWithRates",
        "result": _validate_moodtrip_payload(
            payload,
            tool_name="searchHotelsWithRates",
            output_model=MoodTripSearchHotelsWithRatesOutput,
        ),
    }


@tool(args_schema=MoodTripHotelDetailsArgs)
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
        "result": _validate_moodtrip_payload(
            payload,
            tool_name="getHotelDetails",
            output_model=MoodTripHotelDetailsOutput,
        ),
    }


@tool(args_schema=MoodTripHotelReviewsArgs)
async def get_accommodation_reviews(
    hotel_id: str,
    get_sentiment: bool = False,
) -> dict[str, Any]:
    """Fetch hotel reviews using MoodTrip through its MCP server."""
    moodtrip_tool = await _get_moodtrip_tool("getHotelReviews")

    moodtrip_args: dict[str, Any] = {
        "hotelId": hotel_id,
        "getSentiment": get_sentiment,
    }

    raw_result = await moodtrip_tool.ainvoke(moodtrip_args)
    payload = _extract_moodtrip_payload(raw_result)
    return {
        "provider": "moodtrip",
        "tool": "getHotelReviews",
        "hotel_id": hotel_id,
        "result": _validate_moodtrip_payload(
            payload,
            tool_name="getHotelReviews",
            output_model=MoodTripHotelReviewsOutput,
        ),
    }


@tool(args_schema=FinishAccommodationSearchArgs)
def finish_accommodation_search(reason: str) -> dict[str, str]:
    """Call this when enough accommodation data has been gathered for ranking."""
    return {"status": "finished", "reason": reason}
