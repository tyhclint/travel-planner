from app.domain.models.accommodations import AccommodationOption
from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.services.accommodations.base import AccommodationService


class MockAccommodationService(AccommodationService):
    def search_accommodations(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[AccommodationOption]:
        destination = requirements.destination or "Tokyo"
        return [
            AccommodationOption(
                id="stay-1",
                name=f"{destination} Central Rooms",
                location=f"Central {destination}",
                rating=4.1,
                nightly_price=120,
                total_price=480,
                currency=requirements.currency,
                amenities=["wifi", "transit nearby"],
            ),
            AccommodationOption(
                id="stay-2",
                name=f"{destination} Grand Hotel",
                location=f"Downtown {destination}",
                rating=4.8,
                nightly_price=260,
                total_price=1040,
                currency=requirements.currency,
                amenities=["wifi", "spa", "breakfast"],
            ),
        ]
