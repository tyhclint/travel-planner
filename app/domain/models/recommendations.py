from pydantic import BaseModel


class DestinationRecommendation(BaseModel):
    name: str
    category: str
    description: str
    location: str | None = None
    estimated_cost: float | None = None
    opening_hours: str | None = None
    source_url: str | None = None
