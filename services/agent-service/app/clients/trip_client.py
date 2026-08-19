import httpx

from app.core.config import get_settings
from app.domain.models.accommodations import AccommodationOption
from app.domain.models.flights import FlightOption
from app.domain.models.preferences import TravelPreferences
from app.domain.models.recommendations import DestinationRecommendation
from app.domain.models.trip import TripRequirements


class TripServiceClient:
    """HTTP client communicating with trip-service microservice."""

    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.trip_service_url).rstrip("/")

    def search_flights(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[FlightOption]:
        payload = {
            "origin": requirements.origin or "Singapore",
            "destination": requirements.destination or "Tokyo",
            "cabin_class": preferences.flight_style if preferences.flight_style in ["economy", "premium_economy", "business", "first"] else "economy",
            "departure_date": str(requirements.departure_date) if requirements.departure_date else None,
            "return_date": str(requirements.return_date) if requirements.return_date else None,
            "currency": requirements.currency,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(f"{self.base_url}/api/flights/search", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return [FlightOption.model_validate(item) for item in data.get("flights", [])]
        except Exception:
            pass
        return []

    def search_accommodations(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[AccommodationOption]:
        payload = {
            "destination": requirements.destination or "Tokyo",
            "accommodation_style": preferences.accommodation_style,
            "accommodation_priority": preferences.accommodation_priority,
            "currency": requirements.currency,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(f"{self.base_url}/api/accommodations/search", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return [AccommodationOption.model_validate(item) for item in data.get("accommodations", [])]
        except Exception:
            pass
        return []

    def search_destination(
        self,
        requirements: TripRequirements,
        preferences: TravelPreferences,
    ) -> list[DestinationRecommendation]:
        payload = {
            "destination": requirements.destination or "Tokyo",
            "interests": preferences.interests,
            "pace": preferences.activity_pace,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(f"{self.base_url}/api/destinations/research", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return [DestinationRecommendation.model_validate(item) for item in data.get("recommendations", [])]
        except Exception:
            pass
        return []
