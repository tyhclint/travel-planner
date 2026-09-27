from typing import Any

from pydantic import RootModel


class MoodTripToolOutput(RootModel[dict[str, Any]]):
    """Generic MoodTrip MCP output until tool-specific payload models are added."""
