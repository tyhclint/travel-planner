from datetime import UTC, datetime, timedelta

from app.domain.models.flights import FlightOption
from app.domain.models.preferences import TravelPreferences
from app.domain.scoring import rank_flights


def test_rank_flights_sorts_price_low_to_high_by_default():
    ranked = rank_flights(_flight_options(), TravelPreferences())

    assert [option.id for option in ranked] == ["cheap", "mid", "premium"]


def test_rank_flights_sorts_price_high_to_low_for_luxurious_flight_style():
    ranked = rank_flights(
        _flight_options(),
        TravelPreferences(flight_style="luxurious"),
    )

    assert [option.id for option in ranked] == ["premium", "mid", "cheap"]


def test_rank_flights_ignores_convenience_priority_for_now():
    ranked = rank_flights(
        _flight_options(),
        TravelPreferences(flight_priority="most_convenient"),
    )

    assert [option.id for option in ranked] == ["cheap", "mid", "premium"]


def _flight_options() -> list[FlightOption]:
    departure = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    return [
        FlightOption(
            id="premium",
            airline="Direct Premium",
            origin="Singapore",
            destination="Tokyo",
            departure_time=departure,
            arrival_time=departure + timedelta(hours=7),
            duration_minutes=420,
            stops=0,
            total_price=900,
        ),
        FlightOption(
            id="cheap",
            airline="Budget Long Route",
            origin="Singapore",
            destination="Tokyo",
            departure_time=departure,
            arrival_time=departure + timedelta(hours=13),
            duration_minutes=780,
            stops=2,
            total_price=300,
        ),
        FlightOption(
            id="mid",
            airline="Middle Air",
            origin="Singapore",
            destination="Tokyo",
            departure_time=departure,
            arrival_time=departure + timedelta(hours=9),
            duration_minutes=540,
            stops=1,
            total_price=500,
        ),
    ]
