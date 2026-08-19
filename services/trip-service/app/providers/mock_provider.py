from datetime import UTC, datetime, timedelta


class MockTripProvider:
    """Deterministic fallback provider for flights and accommodations."""

    @staticmethod
    def get_flights(
        origin: str = "Singapore",
        destination: str = "Tokyo",
        cabin_class: str = "economy",
        currency: str = "USD",
    ) -> list[dict]:
        departure = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
        return [
            {
                "id": "fl-trip-1",
                "airline": "Singapore Airlines",
                "origin": origin,
                "destination": destination,
                "departure_time": departure.isoformat(),
                "arrival_time": (departure + timedelta(hours=7)).isoformat(),
                "duration_minutes": 420,
                "stops": 0,
                "cabin_class": cabin_class,
                "baggage_description": "25kg checked baggage included",
                "total_price": 540.0,
                "currency": currency,
                "provider": "Trip.com",
                "booking_url": f"https://www.trip.com/flights/{origin}-to-{destination}",
            },
            {
                "id": "fl-trip-2",
                "airline": "Scoot / AirAsia",
                "origin": origin,
                "destination": destination,
                "departure_time": (departure + timedelta(hours=2)).isoformat(),
                "arrival_time": (departure + timedelta(hours=11)).isoformat(),
                "duration_minutes": 540,
                "stops": 1,
                "cabin_class": cabin_class,
                "baggage_description": "Cabin bag only (7kg)",
                "total_price": 290.0,
                "currency": currency,
                "provider": "Trip.com",
                "booking_url": f"https://www.trip.com/flights/{origin}-to-{destination}",
            },
            {
                "id": "fl-trip-3",
                "airline": "ANA All Nippon Airways",
                "origin": origin,
                "destination": destination,
                "departure_time": (departure + timedelta(hours=6)).isoformat(),
                "arrival_time": (departure + timedelta(hours=13, minutes=30)).isoformat(),
                "duration_minutes": 450,
                "stops": 0,
                "cabin_class": "business" if cabin_class == "business" else "economy",
                "baggage_description": "2x 32kg checked bags included",
                "total_price": 880.0,
                "currency": currency,
                "provider": "Trip.com",
                "booking_url": f"https://www.trip.com/flights/{origin}-to-{destination}",
            },
        ]

    @staticmethod
    def get_accommodations(
        destination: str = "Tokyo",
        style: str = "standard",
        currency: str = "USD",
    ) -> list[dict]:
        return [
            {
                "id": "acc-trip-1",
                "name": f"{destination} Shibuya Sky View Hotel",
                "accommodation_type": "hotel",
                "location": f"Shibuya, {destination}",
                "latitude": 35.6580,
                "longitude": 139.7016,
                "rating": 4.6,
                "nightly_price": 140.0,
                "total_price": 560.0,
                "currency": currency,
                "amenities": ["Free High-Speed WiFi", "Walking distance to metro", "24/7 Front Desk"],
                "provider": "Trip.com",
                "booking_url": f"https://www.trip.com/hotels/{destination}",
            },
            {
                "id": "acc-trip-2",
                "name": f"{destination} Capsule & Pods Cozy Stay",
                "accommodation_type": "hostel",
                "location": f"Asakusa, {destination}",
                "latitude": 35.7118,
                "longitude": 139.7967,
                "rating": 4.2,
                "nightly_price": 45.0,
                "total_price": 180.0,
                "currency": currency,
                "amenities": ["Free WiFi", "Lockers", "Shared Lounge"],
                "provider": "Trip.com",
                "booking_url": f"https://www.trip.com/hotels/{destination}",
            },
            {
                "id": "acc-trip-3",
                "name": f"{destination} Imperial Luxury Suites",
                "accommodation_type": "luxury_hotel",
                "location": f"Ginza, {destination}",
                "latitude": 35.6719,
                "longitude": 139.7649,
                "rating": 4.9,
                "nightly_price": 380.0,
                "total_price": 1520.0,
                "currency": currency,
                "amenities": ["Spa & Onsen", "Michelin Dining", "Panoramic Skyline", "Concierge"],
                "provider": "Trip.com",
                "booking_url": f"https://www.trip.com/hotels/{destination}",
            },
        ]
