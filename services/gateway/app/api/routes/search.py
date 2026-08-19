from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    AccommodationSearchRequest,
    DestinationResearchRequest,
    FlightSearchRequest,
)
from app.clients.trip_client import TripServiceClient

router = APIRouter(prefix="/search", tags=["search"])
trip_client = TripServiceClient()


@router.post("/flights")
async def search_flights(request: FlightSearchRequest):
    try:
        return await trip_client.search_flights(request.model_dump())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Trip service error: {e}") from e


@router.post("/accommodations")
async def search_accommodations(request: AccommodationSearchRequest):
    try:
        return await trip_client.search_accommodations(request.model_dump())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Trip service error: {e}") from e


@router.post("/destinations")
async def research_destinations(request: DestinationResearchRequest):
    try:
        return await trip_client.research_destinations(request.model_dump())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Trip service error: {e}") from e
