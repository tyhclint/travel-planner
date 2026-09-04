from pydantic import BaseModel


class AgentError(BaseModel):
    source: str
    error_type: str
    message: str
    retryable: bool = False


class TurnInterpreterError(Exception):
    """Raised when the LLM turn interpreter cannot produce valid structured output."""


class OrchestratorError(Exception):
    """Raised when the LLM orchestrator cannot produce valid structured output."""
