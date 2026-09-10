from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.travel import router as travel_router
from app.mcp import mcp
from app.services.search.rag import MarkdownDestinationIndexer


mcp_http_app = mcp.streamable_http_app(streamable_http_path="/")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    del _app
    MarkdownDestinationIndexer().index_documents()
    async with mcp_http_app.router.lifespan_context(mcp_http_app):
        yield


app = FastAPI(title="Travel Planner", version="0.1.0", lifespan=lifespan)
app.include_router(travel_router, prefix="/api")
app.mount("/mcp", mcp_http_app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
