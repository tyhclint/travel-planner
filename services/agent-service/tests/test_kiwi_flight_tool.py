import asyncio
from datetime import date

import pytest

from app.services.flights import tools as flight_tools
from app.services.flights.errors import KiwiPayloadValidationError


class FakeKiwiTool:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def ainvoke(self, args):
        self.calls.append(args)
        return self.payload


def test_search_flights_validates_and_returns_kiwi_output(monkeypatch):
    fake_tool = FakeKiwiTool(
        {
            "query": "Singapore to Tokyo",
            "currency": "USD",
            "passengers": {"adults": 1, "children": 0, "infants": 0},
            "resultsCount": 1,
            "itineraries": [
                {
                    "id": "itinerary-1",
                    "price": 320,
                    "priceFormatted": "320 USD",
                    "totalDurationSeconds": 25200,
                    "bookingUrl": "https://example.test/booking",
                    "baggage": {
                        "personalItem": 1,
                        "cabinBag": 1,
                        "checkedBag": 0,
                    },
                    "outbound": {
                        "from": "SIN",
                        "to": "NRT",
                        "departureTime": "2026-10-01T08:00:00",
                        "arrivalTime": "2026-10-01T15:00:00",
                        "durationSeconds": 25200,
                        "stops": 0,
                        "route": ["SIN", "NRT"],
                        "cabinClass": "Economy",
                        "segments": [
                            {
                                "from": "SIN",
                                "to": "NRT",
                                "carrier": "TR",
                                "carrierName": "Scoot",
                            }
                        ],
                    },
                }
            ],
            "searchTimeMs": 123,
        }
    )

    async def fake_get_kiwi_search_flight_tool():
        return fake_tool

    monkeypatch.setattr(
        flight_tools,
        "_get_kiwi_search_flight_tool",
        fake_get_kiwi_search_flight_tool,
    )

    result = asyncio.run(
        flight_tools.search_flights.ainvoke(
            {
                "fly_from": "Singapore",
                "fly_to": "Tokyo",
                "departure_date": date(2026, 10, 1),
                "adults": 1,
                "currency": "usd",
            }
        )
    )

    assert fake_tool.calls[0]["currency"] == "USD"
    assert result["provider"] == "kiwi"
    assert result["result"]["query"] == "Singapore to Tokyo"
    assert result["result"]["itineraries"][0]["outbound"]["segments"][0]["from"] == "SIN"


def test_search_flights_rejects_invalid_kiwi_output(monkeypatch):
    fake_tool = FakeKiwiTool({"currency": "USD", "itineraries": []})

    async def fake_get_kiwi_search_flight_tool():
        return fake_tool

    monkeypatch.setattr(
        flight_tools,
        "_get_kiwi_search_flight_tool",
        fake_get_kiwi_search_flight_tool,
    )

    with pytest.raises(KiwiPayloadValidationError):
        asyncio.run(
            flight_tools.search_flights.ainvoke(
                {
                    "fly_from": "Singapore",
                    "fly_to": "Tokyo",
                    "departure_date": date(2026, 10, 1),
                }
            )
        )
