from app.domain.models.accommodations import AccommodationOption
from app.domain.models.flights import FlightOption
from app.domain.models.itinerary import Activity, Itinerary, ItineraryDay
from app.domain.models.preferences import TravelPreferences
from app.domain.models.recommendations import DestinationRecommendation
from app.domain.models.trip import TripRequirements

__all__ = [
    "AccommodationOption",
    "Activity",
    "DestinationRecommendation",
    "FlightOption",
    "Itinerary",
    "ItineraryDay",
    "TravelPreferences",
    "TripRequirements",
]
