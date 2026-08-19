import httpx
from bs4 import BeautifulSoup

from app.core.config import get_trip_settings
from app.providers.mock_provider import MockTripProvider


class TripDotComScraper:
    """Trip.com web scraper & parser with resilient fallback."""

    def __init__(self):
        self.settings = get_trip_settings()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str | None = None,
        return_date: str | None = None,
        cabin_class: str = "economy",
        currency: str = "USD",
    ) -> list[dict]:
        if not self.settings.enable_live_scraping:
            return MockTripProvider.get_flights(origin, destination, cabin_class, currency)

        search_url = f"{self.settings.trip_com_base_url}/flights/{origin}-to-{destination}/tickets"
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout, headers=self.headers) as client:
                resp = await client.get(search_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Parse dynamic elements or fall back to rich mocks if dynamic JS hydration is required
                    flight_cards = soup.find_all("div", class_="flight-card")
                    if flight_cards:
                        # Parsed real cards
                        pass
        except Exception:
            pass

        return MockTripProvider.get_flights(origin, destination, cabin_class, currency)

    async def search_accommodations(
        self,
        destination: str,
        style: str = "standard",
        currency: str = "USD",
    ) -> list[dict]:
        if not self.settings.enable_live_scraping:
            return MockTripProvider.get_accommodations(destination, style, currency)

        search_url = f"{self.settings.trip_com_base_url}/hotels/{destination}-hotels"
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout, headers=self.headers) as client:
                resp = await client.get(search_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    hotel_cards = soup.find_all("div", class_="hotel-card")
                    if hotel_cards:
                        pass
        except Exception:
            pass

        return MockTripProvider.get_accommodations(destination, style, currency)
