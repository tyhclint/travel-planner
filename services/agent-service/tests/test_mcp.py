from app.domain.models.preferences import TravelPreferences
from app.domain.models.trip import TripRequirements
from app.services.mcp.registry import MCPToolRegistry
from app.services.mcp.travel import MCPTravelService


def test_local_mcp_registry_exposes_travel_tools():
    service = MCPTravelService()
    tools = {tool["name"] for tool in service.registry.list_tools()}
    assert tools == {
        "travel.search_flights",
        "travel.search_accommodations",
        "travel.search_destination",
    }


def test_mcp_travel_service_normalizes_tool_results():
    service = MCPTravelService()
    results = service.search_flights(
        TripRequirements(origin="Singapore", destination="Tokyo"),
        TravelPreferences(),
    )
    assert results
    assert results[0].origin == "Singapore"
    assert results[0].destination == "Tokyo"


def test_registry_rejects_unknown_tools():
    registry = MCPToolRegistry()
    try:
        registry.call_tool("travel.unknown", {})
    except ValueError as exc:
        assert "Unknown MCP tool" in str(exc)
    else:
        raise AssertionError("Unknown tools must be rejected")
