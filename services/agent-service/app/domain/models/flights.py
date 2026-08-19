from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CabinClass = Literal["economy", "premium_economy", "business", "first"]


class FlightOption(BaseModel):
    id: str
    airline: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int = Field(gt=0)
    stops: int = Field(ge=0)
    cabin_class: CabinClass
    baggage_description: str | None = None
    total_price: float = Field(ge=0)
    currency: str = "USD"
    provider: str = "mock"
    booking_url: str | None = None
