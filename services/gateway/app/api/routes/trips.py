from fastapi import APIRouter, HTTPException

from app.api.schemas import TripCreateRequest
from app.clients.db_client import DBServiceClient

router = APIRouter(prefix="/trips", tags=["trips"])
db_client = DBServiceClient()


@router.get("")
async def list_trips(user_id: str | None = None):
    try:
        return await db_client.list_trips(user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Database service error: {e}") from e


@router.post("", status_code=201)
async def create_trip(request: TripCreateRequest):
    try:
        return await db_client.create_trip(request.model_dump())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Database service error: {e}") from e


@router.get("/{trip_id}")
async def get_trip(trip_id: str):
    try:
        return await db_client.get_trip(trip_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Database service error: {e}") from e


@router.put("/{trip_id}")
async def update_trip(trip_id: str, request: dict):
    try:
        return await db_client.update_trip(trip_id, request)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Database service error: {e}") from e


@router.delete("/{trip_id}")
async def delete_trip(trip_id: str):
    try:
        return await db_client.delete_trip(trip_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Database service error: {e}") from e
