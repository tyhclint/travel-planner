from fastapi import APIRouter

from app.api.schemas import FlightSearchRequest, FlightSearchResponse
from app.providers.trip_scraper import TripDotComScraper

router = APIRouter(prefix="/flights", tags=["flights"])
scraper = TripDotComScraper()


@router.post("/search", response_model=FlightSearchResponse)
async def search_flights(payload: FlightSearchRequest) -> FlightSearchResponse:
    flights = await scraper.search_flights(
        origin=payload.origin,
        destination=payload.destination,
        departure_date=payload.departure_date,
        return_date=payload.return_date,
        cabin_class=payload.cabin_class,
        currency=payload.currency,
    )
    return FlightSearchResponse(
        origin=payload.origin,
        destination=payload.destination,
        flights=flights,
    )
