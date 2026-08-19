from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationDocument(BaseModel):
    thread_id: str = Field(..., alias="_id")
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        populate_by_name = True
