from datetime import date

from pydantic import BaseModel, Field


class AccommodationOption(BaseModel):
    id: str
    name: str
    accommodation_type: str = "hotel"
    location: str
    latitude: float | None = None
    longitude: float | None = None
    check_in: date | None = None
    check_out: date | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    nightly_price: float = Field(ge=0)
    total_price: float = Field(ge=0)
    currency: str = "USD"
    amenities: list[str] = Field(default_factory=list)
    provider: str = "mock"
    booking_url: str | None = None
