from pydantic import BaseModel

class LLMProviderError(Exception):
    """Raised when the LLM provider returns an error response or no api key set."""


class AgentError(BaseModel):
    source: str
    error_type: str
    message: str
    retryable: bool = False


class TurnInterpreterError(Exception):
    """Raised when the LLM turn interpreter cannot produce valid structured output."""


class OrchestratorError(Exception):
    """Raised when the LLM orchestrator cannot produce valid structured output."""


class ItineraryPlannerError(Exception):
    """Raised when the LLM itinerary planner cannot produce valid structured output."""
