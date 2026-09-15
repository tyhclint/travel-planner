"""Inspect Kiwi MCP tool definitions without executing a flight search.

Run from services/agent-service:
    python -m app.scripts.inspect_kiwi_tool_schema
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from app.services.flights.mcp import KIWI_MCP_SERVER_NAME, get_flight_mcp_client

DEFAULT_OUTPUT_PATH = Path("app/scripts/kiwi_tool_schema.json")


def parse_args() -> argparse.Namespace:
    """Parse CLI options for the schema inspection script."""
    parser = argparse.ArgumentParser(
        description="List Kiwi MCP tool schemas without calling search-flight."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the raw tools/list response JSON.",
    )
    return parser.parse_args()


async def main() -> None:
    """Call MCP tools/list and report whether each tool has an output schema."""
    _configure_utf8_output()
    args = parse_args()
    tools = await _list_tools()
    payload = [_json_safe(tool) for tool in tools]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print(f"Found {len(tools)} Kiwi MCP tool(s).")
    print(f"Saved tools/list payload to: {args.output}")

    for tool in tools:
        tool_data = _json_safe(tool)
        name = tool_data.get("name", "<unknown>")
        input_schema = tool_data.get("inputSchema")
        output_schema = tool_data.get("outputSchema")

        print(f"\nTool: {name}")
        print(f"Description: {tool_data.get('description') or ''}")
        print(f"Has inputSchema: {input_schema is not None}")
        print(f"Has outputSchema: {output_schema is not None}")

        if input_schema is not None:
            print("Input schema:")
            print(json.dumps(input_schema, indent=2, default=str))

        if output_schema is not None:
            print("Output schema:")
            print(json.dumps(output_schema, indent=2, default=str))


async def _list_tools() -> list[Any]:
    """Open a Kiwi MCP session and call tools/list with pagination support."""
    client = get_flight_mcp_client()
    all_tools: list[Any] = []
    cursor: str | None = None

    async with client.session(KIWI_MCP_SERVER_NAME) as session:
        while True:
            result = await session.list_tools(cursor=cursor)
            all_tools.extend(result.tools or [])

            cursor = result.nextCursor
            if not cursor:
                break

    return all_tools


def _configure_utf8_output() -> None:
    """Use UTF-8 when printing redirected output on Windows terminals."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def _json_safe(value: Any) -> Any:
    """Convert MCP/Pydantic objects into JSON-serializable dictionaries."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


if __name__ == "__main__":
    asyncio.run(main())
