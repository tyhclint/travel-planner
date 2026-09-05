from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "trip-service",
        "providers": ["trip.com", "mock_fallback"],
    }
