from app.domain.models.accommodations import AccommodationOption
from app.domain.models.flights import FlightOption
from app.domain.models.preferences import TravelPreferences


def rank_flights(
    options: list[FlightOption],
    preferences: TravelPreferences,
) -> list[FlightOption]:
    reverse_price = preferences.flight_style == "luxurious"
    return sorted(options, key=lambda option: option.total_price, reverse=reverse_price)


def rank_accommodations(
    options: list[AccommodationOption],
    preferences: TravelPreferences,
) -> list[AccommodationOption]:
    if preferences.accommodation_priority == "cheapest":
        return sorted(options, key=lambda option: option.total_price)
    if preferences.accommodation_priority == "most_luxurious":
        return sorted(options, key=lambda option: option.rating or 0, reverse=True)
    return sorted(options, key=lambda option: (-(option.rating or 0), option.total_price))
