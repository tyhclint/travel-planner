import json

from langchain_core.messages import ToolMessage

from app.services.flights.result_parser import parse_flight_tool_messages


def test_parse_flight_tool_messages_maps_kiwi_itineraries_to_flight_options():
    options = parse_flight_tool_messages(
        [
            ToolMessage(
                content=json.dumps(
                    {
                        "provider": "kiwi",
                        "result": {
                            "query": "Singapore to Tokyo",
                            "currency": "USD",
                            "resultsCount": 1,
                            "itineraries": [
                                {
                                    "id": "kiwi-1",
                                    "price": 320,
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
                                        "departureTime": "2026-10-01T08:00:00+00:00",
                                        "arrivalTime": "2026-10-01T15:00:00+00:00",
                                        "durationSeconds": 25200,
                                        "stops": 0,
                                        "route": ["SIN", "NRT"],
                                        "cabinClass": "Economy",
                                        "segments": [
                                            {
                                                "carrier": "TR",
                                                "carrierName": "Scoot",
                                            }
                                        ],
                                    },
                                }
                            ],
                        },
                    }
                ),
                name="search_flights",
                tool_call_id="call-search",
            )
        ]
    )

    assert len(options) == 1
    assert options[0].id == "kiwi-1"
    assert options[0].airline == "Scoot"
    assert options[0].origin == "SIN"
    assert options[0].destination == "NRT"
    assert options[0].duration_minutes == 420
    assert options[0].stops == 0
    assert options[0].cabin_class == "economy"
    assert options[0].total_price == 320
    assert options[0].currency == "USD"
    assert options[0].booking_url == "https://example.test/booking"
