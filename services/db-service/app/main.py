from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.routes.bookmarks import router as bookmarks_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.health import router as health_router
from app.api.routes.trips import router as trips_router
from app.core.database import db_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database connection
    try:
        db_manager.connect()
    except Exception:
        pass
    yield
    # Shutdown: close connection
    db_manager.close()


app = FastAPI(
    title="Travel Planner - Database Service",
    description="MongoDB persistence microservice for trips, conversations, and bookmarks",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(trips_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(bookmarks_router, prefix="/api")
