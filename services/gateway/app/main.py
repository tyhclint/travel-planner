from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.search import router as search_router
from app.api.routes.travel import router as travel_router
from app.api.routes.trips import router as trips_router
from app.core.config import get_gateway_settings

settings = get_gateway_settings()

app = FastAPI(
    title="Travel Planner - API Gateway",
    description="Central API Gateway routing Next.js requests to travel-planner microservices",
    version="0.1.0",
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(travel_router, prefix="/api")
app.include_router(trips_router, prefix="/api")
app.include_router(search_router, prefix="/api")
