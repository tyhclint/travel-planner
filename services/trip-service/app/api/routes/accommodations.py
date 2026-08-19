from fastapi import APIRouter

from app.api.schemas import AccommodationSearchRequest, AccommodationSearchResponse
from app.providers.trip_scraper import TripDotComScraper

router = APIRouter(prefix="/accommodations", tags=["accommodations"])
scraper = TripDotComScraper()


@router.post("/search", response_model=AccommodationSearchResponse)
async def search_accommodations(payload: AccommodationSearchRequest) -> AccommodationSearchResponse:
    accommodations = await scraper.search_accommodations(
        destination=payload.destination,
        style=payload.accommodation_style,
        currency=payload.currency,
    )
    return AccommodationSearchResponse(
        destination=payload.destination,
        accommodations=accommodations,
    )
