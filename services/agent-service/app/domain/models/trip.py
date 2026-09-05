from datetime import date

from pydantic import BaseModel, Field


class TripRequirements(BaseModel):
    origin: str | None = None
    destination: str | None = None
    departure_date: date | None = None
    return_date: date | None = None
    trip_length_days: int | None = Field(default=None, ge=1)
    travellers: int = Field(default=1, ge=1)
    budget: float | None = Field(default=None, ge=0)
    currency: str = "USD"
