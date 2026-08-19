from fastapi import APIRouter
from app.core.database import db_manager

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    db_status = "connected"
    try:
        db = db_manager.get_database()
        await db.command("ping")
    except Exception as e:
        db_status = f"disconnected: {e}"

    return {
        "status": "ok" if "disconnected" not in db_status else "degraded",
        "service": "db-service",
        "database": db_status,
    }
