from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TripDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    user_id: str = Field(default="anonymous", index=True)
    title: str
    destination: str
    origin: str | None = None
    trip_length_days: int = 3
    itinerary: dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        populate_by_name = True
