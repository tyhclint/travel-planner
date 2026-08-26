from app.providers.destination_provider import DestinationResearchProvider
from app.providers.mock_provider import MockTripProvider


def test_mock_flights_provider():
    flights = MockTripProvider.get_flights(origin="Singapore", destination="Tokyo")
    assert len(flights) >= 2
    assert any(f["stops"] == 0 for f in flights)


def test_mock_accommodations_provider():
    hotels = MockTripProvider.get_accommodations(destination="Tokyo")
    assert len(hotels) >= 2
    assert any("WiFi" in str(h["amenities"]) for h in hotels)


def test_destination_provider():
    recs = DestinationResearchProvider.get_recommendations(destination="Tokyo")
    assert len(recs) >= 3
    names = [r["name"] for r in recs]
    assert any("Senso-ji" in n for n in names)
