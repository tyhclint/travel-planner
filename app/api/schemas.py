from pydantic import BaseModel, Field


class TravelStreamRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
