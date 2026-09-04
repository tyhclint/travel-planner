"""MCP server exposing the travel planner directly to MCP-capable clients."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.services.mcp.registry import get_local_registry
from app.services.mcp.workflow import run_travel_turn

mcp = FastMCP("travel-planner")


@mcp.tool()
def plan_travel(message: str, thread_id: str = "mcp-default") -> str:
    """Plan or revise a trip using the checkpointed LangGraph workflow.

    Reuse the same thread_id for follow-up messages.
    """
    return run_travel_turn(message, thread_id)


@mcp.tool()
def list_travel_capabilities() -> str:
    """List the lower-level travel capabilities used by the planner."""
    return json.dumps([tool["name"] for tool in get_local_registry().list_tools()])


@mcp.tool()
def search_flights(requirements: dict[str, Any], preferences: dict[str, Any]) -> str:
    """Directly search normalized flight options."""
    values = get_local_registry().call_tool("travel.search_flights", {"requirements": requirements, "preferences": preferences})
    return json.dumps(values)


@mcp.tool()
def search_accommodations(requirements: dict[str, Any], preferences: dict[str, Any]) -> str:
    """Directly search normalized accommodation options."""
    values = get_local_registry().call_tool("travel.search_accommodations", {"requirements": requirements, "preferences": preferences})
    return json.dumps(values)


@mcp.tool()
def search_destination(requirements: dict[str, Any], preferences: dict[str, Any]) -> str:
    """Directly search normalized destination recommendations."""
    values = get_local_registry().call_tool("travel.search_destination", {"requirements": requirements, "preferences": preferences})
    return json.dumps(values)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
