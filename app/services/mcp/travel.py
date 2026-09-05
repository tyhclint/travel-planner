"""Graph-facing adapters that consume the local MCP tool boundary."""

from app.domain.models.accommodations import AccommodationOption
from app.domain.models.flights import FlightOption
from app.domain.models.preferences import TravelPreferences
from app.domain.models.recommendations import DestinationRecommendation
from app.domain.models.trip import TripRequirements
from app.services.mcp.registry import MCPToolRegistry, get_local_registry


class MCPTravelService:
    def __init__(self, registry: MCPToolRegistry | None = None) -> None:
        self.registry = registry or get_local_registry()

    def search_flights(self, requirements: TripRequirements, preferences: TravelPreferences) -> list[FlightOption]:
        values = self.registry.call_tool("travel.search_flights", _args(requirements, preferences))
        return [FlightOption.model_validate(value) for value in values]

    def search_accommodations(self, requirements: TripRequirements, preferences: TravelPreferences) -> list[AccommodationOption]:
        values = self.registry.call_tool("travel.search_accommodations", _args(requirements, preferences))
        return [AccommodationOption.model_validate(value) for value in values]

    def search_destination(self, requirements: TripRequirements, preferences: TravelPreferences) -> list[DestinationRecommendation]:
        values = self.registry.call_tool("travel.search_destination", _args(requirements, preferences))
        return [DestinationRecommendation.model_validate(value) for value in values]


def _args(requirements: TripRequirements, preferences: TravelPreferences) -> dict[str, dict]:
    return {"requirements": requirements.model_dump(mode="json"), "preferences": preferences.model_dump(mode="json")}
