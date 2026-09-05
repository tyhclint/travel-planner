from app.clients.trip_client import TripServiceClient
from app.domain.models.accommodations import AccommodationOption
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.services.accommodations.base import AccommodationService
from app.services.accommodations.mock import MockAccommodationService


class TripServiceAccommodationAdapter(AccommodationService):
    """Accommodation adapter delegating to trip-service over HTTP with mock fallback."""

    def __init__(self):
        self.client = TripServiceClient()
        self.fallback = MockAccommodationService()

    def search_accommodations(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[AccommodationOption]:
        results = self.client.search_accommodations(requirements, preferences)
        if results:
            return results
        return self.fallback.search_accommodations(requirements, preferences)
