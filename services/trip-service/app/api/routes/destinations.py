from fastapi import APIRouter

from app.api.schemas import DestinationResearchRequest, DestinationResearchResponse
from app.providers.destination_provider import DestinationResearchProvider

router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.post("/research", response_model=DestinationResearchResponse)
async def research_destination(payload: DestinationResearchRequest) -> DestinationResearchResponse:
    recommendations = DestinationResearchProvider.get_recommendations(
        destination=payload.destination,
        interests=payload.interests,
        pace=payload.pace,
    )
    return DestinationResearchResponse(
        destination=payload.destination,
        recommendations=recommendations,
    )
