from datetime import datetime
from pydantic import BaseModel, Field


class FlightSearchRequest(BaseModel):
    origin: str = "Singapore"
    destination: str = "Tokyo"
    departure_date: str | None = None
    return_date: str | None = None
    cabin_class: str = "economy"
    currency: str = "USD"


class FlightSearchResponse(BaseModel):
    origin: str
    destination: str
    flights: list[dict] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AccommodationSearchRequest(BaseModel):
    destination: str = "Tokyo"
    accommodation_style: str = "standard"
    accommodation_priority: str = "balanced"
    currency: str = "USD"


class AccommodationSearchResponse(BaseModel):
    destination: str
    accommodations: list[dict] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DestinationResearchRequest(BaseModel):
    destination: str = "Tokyo"
    interests: list[str] = Field(default_factory=list)
    pace: str = "balanced"


class DestinationResearchResponse(BaseModel):
    destination: str
    recommendations: list[dict] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
