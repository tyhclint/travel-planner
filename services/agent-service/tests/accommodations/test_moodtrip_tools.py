import asyncio
from datetime import date

import pytest

from app.services.accommodations import tools as accommodation_tools
from app.services.accommodations.errors import MoodTripPayloadValidationError


class FakeMoodTripTool:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def ainvoke(self, args):
        self.calls.append(args)
        return self.payload


def test_search_accommodations_validates_and_returns_moodtrip_output(monkeypatch):
    fake_tool = FakeMoodTripTool(
        {
            "checkIn": "2026-10-01",
            "checkOut": "2026-10-05",
            "currency": "USD",
            "hotels": [
                {
                    "id": "hotel-1",
                    "name": "Tokyo Central Hotel",
                    "city": "Tokyo",
                    "rating": 4.4,
                    "price": {"nightly": 150, "total": 600, "currency": "USD"},
                }
            ],
        }
    )

    async def fake_get_moodtrip_tool(tool_name):
        assert tool_name == "searchHotelsWithRates"
        return fake_tool

    monkeypatch.setattr(accommodation_tools, "_get_moodtrip_tool", fake_get_moodtrip_tool)

    result = asyncio.run(
        accommodation_tools.search_accommodations.ainvoke(
            {
                "city_name": "Tokyo",
                "country_code": "JP",
                "checkin": date(2026, 10, 1),
                "checkout": date(2026, 10, 5),
                "occupancies": [{"adults": 2, "children": []}],
                "currency": "usd",
                "max_price": 200,
                "limit": 3,
            }
        )
    )

    assert fake_tool.calls[0]["cityName"] == "Tokyo"
    assert fake_tool.calls[0]["countryCode"] == "JP"
    assert fake_tool.calls[0]["checkin"] == "2026-10-01"
    assert fake_tool.calls[0]["checkout"] == "2026-10-05"
    assert fake_tool.calls[0]["occupancies"] == [{"adults": 2, "children": []}]
    assert fake_tool.calls[0]["currency"] == "USD"
    assert fake_tool.calls[0]["maxPrice"] == 200
    assert fake_tool.calls[0]["limit"] == 3
    assert result["provider"] == "moodtrip"
    assert result["tool"] == "searchHotelsWithRates"
    assert result["result"]["hotels"][0]["id"] == "hotel-1"


def test_get_accommodation_reviews_validates_and_returns_moodtrip_output(monkeypatch):
    fake_tool = FakeMoodTripTool(
        {
            "hotelId": "hotel-1",
            "summary": "Great location and quiet rooms.",
            "averageRating": 4.7,
            "reviews": [],
        }
    )

    async def fake_get_moodtrip_tool(tool_name):
        assert tool_name == "getHotelReviews"
        return fake_tool

    monkeypatch.setattr(accommodation_tools, "_get_moodtrip_tool", fake_get_moodtrip_tool)

    result = asyncio.run(
        accommodation_tools.get_accommodation_reviews.ainvoke(
            {
                "hotel_id": "hotel-1",
                "get_sentiment": True,
            }
        )
    )

    assert fake_tool.calls[0] == {"hotelId": "hotel-1", "getSentiment": True}
    assert result["provider"] == "moodtrip"
    assert result["tool"] == "getHotelReviews"
    assert result["hotel_id"] == "hotel-1"
    assert result["result"]["summary"] == "Great location and quiet rooms."


def test_search_accommodations_rejects_non_object_moodtrip_output(monkeypatch):
    fake_tool = FakeMoodTripTool(["not", "an", "object"])

    async def fake_get_moodtrip_tool(tool_name):
        return fake_tool

    monkeypatch.setattr(accommodation_tools, "_get_moodtrip_tool", fake_get_moodtrip_tool)

    with pytest.raises(MoodTripPayloadValidationError):
        asyncio.run(
            accommodation_tools.search_accommodations.ainvoke(
                {
                    "city_name": "Tokyo",
                    "country_code": "JP",
                    "checkin": date(2026, 10, 1),
                    "checkout": date(2026, 10, 5),
                    "occupancies": [{"adults": 2, "children": []}],
                }
            )
        )
