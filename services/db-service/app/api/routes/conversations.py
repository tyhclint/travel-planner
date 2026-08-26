from datetime import UTC, datetime
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.schemas import ConversationSave
from app.core.database import get_db
from app.models.conversation_document import ConversationDocument

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/{thread_id}")
async def get_conversation(thread_id: str):
    db: AsyncIOMotorDatabase = get_db()
    doc = await db["conversations"].find_one({"_id": thread_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Conversation thread not found")
    doc["thread_id"] = str(doc.pop("_id"))
    return doc


@router.post("/{thread_id}")
async def save_conversation(thread_id: str, payload: ConversationSave):
    db: AsyncIOMotorDatabase = get_db()
    doc_data = {
        "_id": thread_id,
        "checkpoint": payload.checkpoint,
        "messages": payload.messages,
        "state": payload.state,
        "updated_at": datetime.now(UTC),
    }
    await db["conversations"].update_one(
        {"_id": thread_id},
        {"$set": doc_data},
        upsert=True,
    )
    doc_data["thread_id"] = doc_data.pop("_id")
    return doc_data
