from datetime import UTC, datetime
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.schemas import TripCreate, TripUpdate
from app.core.database import get_db
from app.models.trip_document import TripDocument

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("")
async def list_trips(user_id: str | None = None):
    db: AsyncIOMotorDatabase = get_db()
    query = {"user_id": user_id} if user_id else {}
    cursor = db["trips"].find(query).sort("created_at", -1)
    trips = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        trips.append(doc)
    return trips


@router.post("", status_code=201)
async def create_trip(payload: TripCreate):
    db: AsyncIOMotorDatabase = get_db()
    trip_doc = TripDocument(**payload.model_dump())
    doc_dict = trip_doc.model_dump(by_alias=True)
    await db["trips"].insert_one(doc_dict)
    doc_dict["id"] = doc_dict.pop("_id")
    return doc_dict


@router.get("/{trip_id}")
async def get_trip(trip_id: str):
    db: AsyncIOMotorDatabase = get_db()
    doc = await db["trips"].find_one({"_id": trip_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Trip not found")
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.put("/{trip_id}")
async def update_trip(trip_id: str, payload: TripUpdate):
    db: AsyncIOMotorDatabase = get_db()
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(UTC)

    result = await db["trips"].update_one({"_id": trip_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Trip not found")

    updated_doc = await db["trips"].find_one({"_id": trip_id})
    updated_doc["id"] = str(updated_doc.pop("_id"))
    return updated_doc


@router.delete("/{trip_id}")
async def delete_trip(trip_id: str):
    db: AsyncIOMotorDatabase = get_db()
    result = await db["trips"].delete_one({"_id": trip_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"deleted": True, "trip_id": trip_id}
