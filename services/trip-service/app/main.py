from fastapi import FastAPI

from app.api.routes.accommodations import router as accommodations_router
from app.api.routes.destinations import router as destinations_router
from app.api.routes.flights import router as flights_router
from app.api.routes.health import router as health_router

app = FastAPI(
    title="Travel Planner - Trip Service",
    description="Provider microservice scraping and querying flight, hotel, and destination POI data",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(flights_router, prefix="/api")
app.include_router(accommodations_router, prefix="/api")
app.include_router(destinations_router, prefix="/api")
