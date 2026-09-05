from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.schemas import BookmarkCreate
from app.core.database import get_db
from app.models.bookmark_document import BookmarkDocument

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.get("")
async def list_bookmarks(user_id: str | None = None):
    db: AsyncIOMotorDatabase = get_db()
    query = {"user_id": user_id} if user_id else {}
    cursor = db["bookmarks"].find(query).sort("created_at", -1)
    bookmarks = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        bookmarks.append(doc)
    return bookmarks


@router.post("", status_code=201)
async def create_bookmark(payload: BookmarkCreate):
    db: AsyncIOMotorDatabase = get_db()
    bookmark = BookmarkDocument(
        user_id=payload.user_id,
        item_type=payload.item_type,
        item_data=payload.item_data,
    )
    doc_dict = bookmark.model_dump(by_alias=True)
    await db["bookmarks"].insert_one(doc_dict)
    doc_dict["id"] = doc_dict.pop("_id")
    return doc_dict


@router.delete("/{bookmark_id}")
async def delete_bookmark(bookmark_id: str):
    db: AsyncIOMotorDatabase = get_db()
    result = await db["bookmarks"].delete_one({"_id": bookmark_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"deleted": True, "bookmark_id": bookmark_id}
