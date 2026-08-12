from pydantic import BaseModel


class AgentError(BaseModel):
    source: str
    error_type: str
    message: str
    retryable: bool = False
