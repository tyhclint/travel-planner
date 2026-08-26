from app.clients.trip_client import TripServiceClient
from app.domain.models.flights import FlightOption
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.services.flights.base import FlightService
from app.services.flights.mock import MockFlightService


class TripServiceFlightAdapter(FlightService):
    """Flight adapter delegating to trip-service over HTTP with mock fallback."""

    def __init__(self):
        self.client = TripServiceClient()
        self.fallback = MockFlightService()

    def search_flights(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[FlightOption]:
        results = self.client.search_flights(requirements, preferences)
        if results:
            return results
        # Fall back to deterministic mock if service is unreachable in dev/test
        return self.fallback.search_flights(requirements, preferences)
