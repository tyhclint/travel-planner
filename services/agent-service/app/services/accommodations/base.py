from typing import Protocol

from app.domain.models.accommodations import AccommodationOption
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements


class AccommodationService(Protocol):
    def search_accommodations(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[AccommodationOption]: ...
