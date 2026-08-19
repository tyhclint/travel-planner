from app.clients.trip_client import TripServiceClient
from app.domain.models.preferences import TravelPreferences
from app.domain.models.recommendations import DestinationRecommendation
from app.domain.models.trip import TripRequirements
from app.services.search.base import SearchService
from app.services.search.mock import MockSearchService


class TripServiceSearchAdapter(SearchService):
    """Destination research adapter delegating to trip-service over HTTP with mock fallback."""

    def __init__(self):
        self.client = TripServiceClient()
        self.fallback = MockSearchService()

    def search_destination(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[DestinationRecommendation]:
        results = self.client.search_destination(requirements, preferences)
        if results:
            return results
        return self.fallback.search_destination(requirements, preferences)
