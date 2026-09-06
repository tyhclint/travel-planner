class KiwiFlightError(RuntimeError):
    """Base error for Kiwi flight provider integration failures."""


class KiwiPayloadValidationError(KiwiFlightError):
    """Raised when Kiwi returns payload data that does not match its MCP schema."""
