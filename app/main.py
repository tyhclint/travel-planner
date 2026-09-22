from contextlib import asynccontextmanager
from fastmcp import Client

from fastapi import FastAPI
from app.mcp.server import mcp
from app.services.search.rag import MarkdownDestinationIndexer

import truststore

truststore.inject_into_ssl()
api_app = FastAPI(title="Travel Planner", version="0.1.0")
KIWI_MCP_DEFAULT_URL = "https://mcp.kiwi.com"


@api_app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

mcp_app = mcp.http_app(path="/mcp")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    del _app
    MarkdownDestinationIndexer().index_documents()
    async with mcp_app.lifespan(mcp_app):
        yield


app = FastAPI(title="Travel Planner", version="0.1.0", lifespan=lifespan)
@app.get("/debug/kiwi-test")
async def debug_kiwi():
    async with Client(KIWI_MCP_DEFAULT_URL, timeout=30.0) as kiwi:
        tools = await kiwi.list_tools()
        return {"tools": [tool.name for tool in tools]}
app.routes.extend(api_app.routes)
app.mount("/", mcp_app)
