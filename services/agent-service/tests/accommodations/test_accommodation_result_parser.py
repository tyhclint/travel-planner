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
                        "result": [
                            {
                                "type": "text",
                                "text": "## MoodTrip Hotel Search Results\n\n"
                                "Found **1 hotels** in **Tokyo** "
                                "(USD 150.00-150.00/night)\n\n"
                                "**Tokyo Central Hotel** ⭐ 8.8/10 | "
                                "**USD 150.00**/night\n"
                                "![Tokyo Central Hotel](https://example.test/image.jpg)\n"
                                "[View & Book](https://moodtrip.ai/hotel/hotel-1?"
                                "checkin=2026-10-01&checkout=2026-10-05&adults=2)\n"
                                "[View Gallery](https://moodtrip.ai/hotel/hotel-1?"
                                "checkin=2026-10-01&checkout=2026-10-05&adults=2)\n",
                                "id": "lc-search",
                            }
                        ],
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
                        "result": [
                            {
                                "type": "text",
                                "text": "**Guest Reviews** (1 total)\n\n"
                                "⭐ 9/10 — Sam (US)\n"
                                "👍 Guests like the transit access and quiet rooms.\n"
                                "_2026-09-19T00:00:00Z_\n",
                                "id": "lc-reviews",
                            }
                        ],
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
    assert options[0].total_price == 150
    assert options[0].currency == "USD"
    assert options[0].amenities == []
    assert options[0].provider == "moodtrip"
    assert options[0].booking_url.startswith("https://moodtrip.ai/hotel/hotel-1")


def test_parse_accommodation_tool_messages_keeps_legacy_dict_payload_support():
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
