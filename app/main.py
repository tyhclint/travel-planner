from fastapi import FastAPI

from app.api.routes.travel import router as travel_router
from app.mcp import mcp
import chromadb

client = chromadb.Client()

app = FastAPI(title="Travel Planner", version="0.1.0")
app.include_router(travel_router, prefix="/api")
app.mount("/mcp", mcp.streamable_http_app())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
