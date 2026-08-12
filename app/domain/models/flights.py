from datetime import datetime

from pydantic import BaseModel, Field


class FlightOption(BaseModel):
    id: str
    airline: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int = Field(gt=0)
    stops: int = Field(ge=0)
    cabin_class: str = "economy"
    baggage_description: str | None = None
    total_price: float = Field(ge=0)
    currency: str = "USD"
    provider: str = "mock"
    booking_url: str | None = None

