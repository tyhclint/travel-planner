from datetime import UTC, datetime, timedelta

from app.domain.models.flights import FlightOption
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.services.flights.base import FlightService


class MockFlightService(FlightService):
    def search_flights(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[FlightOption]:
        origin = requirements.origin or "Singapore"
        destination = requirements.destination or "Tokyo"
        departure = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)

        return [
            FlightOption(
                id="flight-1",
                airline="Mock Air",
                origin=origin,
                destination=destination,
                departure_time=departure,
                arrival_time=departure + timedelta(hours=7),
                duration_minutes=420,
                stops=0,
                cabin_class="economy",
                total_price=420,
                currency=requirements.currency,
            ),
            FlightOption(
                id="flight-2",
                airline="Budget Wings",
                origin=origin,
                destination=destination,
                departure_time=departure + timedelta(hours=3),
                arrival_time=departure + timedelta(hours=12),
                duration_minutes=540,
                stops=1,
                cabin_class="economy",
                total_price=310,
                currency=requirements.currency,
            ),
        ]
