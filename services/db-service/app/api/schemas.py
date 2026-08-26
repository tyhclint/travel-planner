from typing import Any
from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    user_id: str = Field(default="anonymous")
    title: str
    destination: str
    origin: str | None = None
    trip_length_days: int = 3
    itinerary: dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TripUpdate(BaseModel):
    title: str | None = None
    destination: str | None = None
    origin: str | None = None
    trip_length_days: int | None = None
    itinerary: dict[str, Any] | None = None
    status: str | None = None
    metadata: dict[str, Any] | None = None


class ConversationSave(BaseModel):
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)


class BookmarkCreate(BaseModel):
    user_id: str = Field(default="anonymous")
    item_type: str
    item_data: dict[str, Any]
