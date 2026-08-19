from typing import Protocol

from app.domain.models.flights import FlightOption
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements


class FlightService(Protocol):
    def search_flights(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[FlightOption]: ...
