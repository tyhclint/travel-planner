from fastapi import FastAPI

from app.api.routes.travel import router as travel_router

app = FastAPI(title="Travel Planner", version="0.1.0")
app.include_router(travel_router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
