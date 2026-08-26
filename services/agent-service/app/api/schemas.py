from pydantic import BaseModel, Field


class TravelStreamRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class TravelInvokeRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class TravelInvokeResponse(BaseModel):
    thread_id: str
    final_response: str
    task_status: dict[str, str] = Field(default_factory=dict)
