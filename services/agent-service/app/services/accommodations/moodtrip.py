from typing import Any, Literal

from pydantic import BaseModel, RootModel


class MoodTripTextContentBlock(BaseModel):
    """Text content block returned by MoodTrip MCP tools."""

    type: Literal["text"]
    text: str
    id: str


class MoodTripToolOutput(RootModel[dict[str, Any]]):
    """Generic MoodTrip MCP output for tools without inspected payload samples."""


class MoodTripSearchHotelsWithRatesOutput(RootModel[list[MoodTripTextContentBlock]]):
    """Raw output returned by MoodTrip searchHotelsWithRates."""


class MoodTripHotelDetailsOutput(RootModel[list[MoodTripTextContentBlock]]):
    """Raw output returned by MoodTrip getHotelDetails."""


class MoodTripHotelReviewsOutput(RootModel[list[MoodTripTextContentBlock]]):
    """Raw output returned by MoodTrip getHotelReviews."""
