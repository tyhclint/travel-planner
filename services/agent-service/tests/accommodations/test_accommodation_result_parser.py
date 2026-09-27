import json

from langchain_core.messages import ToolMessage

from app.services.accommodations.result_parser import parse_accommodation_tool_messages


def test_parse_accommodation_tool_messages_maps_moodtrip_hotels_to_options():
    options = parse_accommodation_tool_messages(
        [
            ToolMessage(
                content=json.dumps(
                    {
                        "provider": "moodtrip",
                        "tool": "searchHotelsWithRates",
                        "result": {
                            "checkIn": "2026-10-01",
                            "checkOut": "2026-10-05",
                            "currency": "USD",
                            "hotels": [
                                {
                                    "id": "hotel-1",
                                    "name": "Tokyo Central Hotel",
                                    "city": "Tokyo",
                                    "rating": 4.4,
                                    "amenities": ["wifi", "breakfast"],
                                    "price": {
                                        "nightly": 150,
                                        "total": 600,
                                        "currency": "USD",
                                    },
                                    "bookingUrl": "https://example.test/hotel-1",
                                }
                            ],
                        },
                    }
                ),
                name="search_accommodations",
                tool_call_id="call-search",
            ),
            ToolMessage(
                content=json.dumps(
                    {
                        "provider": "moodtrip",
                        "tool": "getHotelReviews",
                        "hotel_id": "hotel-1",
                        "result": {
                            "summary": "Guests like the transit access and quiet rooms.",
                            "averageRating": 4.6,
                        },
                    }
                ),
                name="get_accommodation_reviews",
                tool_call_id="call-reviews",
            ),
        ]
    )

    assert len(options) == 1
    assert options[0].id == "hotel-1"
    assert options[0].name == "Tokyo Central Hotel"
    assert options[0].location == "Tokyo"
    assert options[0].rating == 4.4
    assert options[0].nightly_price == 150
    assert options[0].total_price == 600
    assert options[0].currency == "USD"
    assert options[0].amenities == ["wifi", "breakfast"]
    assert options[0].provider == "moodtrip"
    assert options[0].booking_url == "https://example.test/hotel-1"
