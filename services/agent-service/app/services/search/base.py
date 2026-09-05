from typing import Protocol

from app.domain.models.preferences import TravelPreferences
from app.domain.models.recommendations import DestinationRecommendation
from app.domain.models.trip import TripRequirements


class SearchService(Protocol):
    def search_destination(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[DestinationRecommendation]: ...
