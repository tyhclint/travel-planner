from app.domain.models.preferences import TravelPreferences
from app.domain.models.recommendations import DestinationRecommendation
from app.domain.models.trip import TripRequirements
from app.services.search.base import SearchService


class MockSearchService(SearchService):
    def search_destination(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[DestinationRecommendation]:
        destination = requirements.destination or "Tokyo"
        return [
            DestinationRecommendation(
                name=f"{destination} old town walk",
                category="culture",
                description="A mock cultural route for early itinerary testing.",
            ),
            DestinationRecommendation(
                name=f"{destination} food market",
                category="food",
                description="A mock food stop that can later be replaced by web or MCP search.",
            ),
        ]
