"""Inspect the raw payload shape returned by the Kiwi MCP search-flight tool.

Run from services/agent-service:
    python app/scripts/inspect_kiwi_payload.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import ToolMessage

from app.services.flights.mcp import get_flight_mcp_tools

DEFAULT_OUTPUT_PATH = Path("app/scripts/kiwi_payload_sample.json")


def parse_args() -> argparse.Namespace:
    """Parse CLI options for the sample Kiwi search."""
    parser = argparse.ArgumentParser(
        description="Call the Kiwi MCP search-flight tool and inspect its payload shape."
    )
    parser.add_argument("--fly-from", default="Singapore")
    parser.add_argument("--fly-to", default="Tokyo")
    parser.add_argument("--departure-date", default="01/10/2026")
    parser.add_argument("--return-date", default=None)
    parser.add_argument("--adults", type=int, default=1)
    parser.add_argument("--children", type=int, default=0)
    parser.add_argument("--infants", type=int, default=0)
    parser.add_argument("--cabin-class", default="M")
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--sort", default="price")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the extracted payload JSON.",
    )
    parser.add_argument(
        "--print-limit",
        type=int,
        default=6000,
        help="Max characters of extracted payload JSON to print.",
    )
    return parser.parse_args()


async def main() -> None:
    """Call Kiwi MCP once, print response shape details, and save the payload."""
    args = parse_args()
    tool = await _kiwi_search_tool()
    tool_args = _tool_args(args)

    print(f"Tool name: {tool.name}")
    print(f"Tool args: {json.dumps(tool_args, indent=2)}")

    raw_result = await tool.ainvoke(tool_args)
    payload = _extract_payload(raw_result)

    print(f"\nRaw result type: {type(raw_result).__name__}")
    print(f"Extracted payload type: {type(payload).__name__}")
    print("\nShape summary:")
    print(json.dumps(_shape_summary(payload), indent=2, default=str))

    payload_json = json.dumps(_json_safe(payload), indent=2, default=str)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload_json, encoding="utf-8")
    print(f"\nSaved extracted payload to: {args.output}")

    print("\nExtracted payload preview:")
    print(payload_json[: args.print_limit])
    if len(payload_json) > args.print_limit:
        print(f"\n... truncated at {args.print_limit} characters")


async def _kiwi_search_tool():
    """Load the configured Kiwi MCP search-flight tool."""
    tools = await get_flight_mcp_tools()
    for tool in tools:
        if tool.name == "kiwi_search-flight":
            return tool

    available = ", ".join(tool.name for tool in tools)
    raise RuntimeError(f"kiwi_search-flight not found. Available tools: {available}")


def _tool_args(args: argparse.Namespace) -> dict[str, Any]:
    """Build the raw Kiwi MCP tool args from CLI options."""
    tool_args: dict[str, Any] = {
        "flyFrom": args.fly_from,
        "flyTo": args.fly_to,
        "departureDate": args.departure_date,
        "adults": args.adults,
        "children": args.children,
        "infants": args.infants,
        "cabinClass": args.cabin_class,
        "currency": args.currency,
        "sort": args.sort,
    }
    if args.return_date:
        tool_args["returnDate"] = args.return_date
    return tool_args


def _extract_payload(raw_result: Any) -> Any:
    """Remove LangChain wrapper data so the Kiwi payload can be inspected directly."""
    if isinstance(raw_result, ToolMessage):
        artifact = getattr(raw_result, "artifact", None)
        if isinstance(artifact, dict):
            return artifact.get("structured_content", artifact)
        return raw_result.content

    if isinstance(raw_result, tuple) and len(raw_result) == 2:
        content, artifact = raw_result
        if isinstance(artifact, dict):
            return artifact.get("structured_content", artifact)
        return content

    return raw_result


def _shape_summary(value: Any) -> Any:
    """Create a compact structural summary of nested dict/list payload data."""
    if isinstance(value, dict):
        summary: dict[str, Any] = {"type": "dict", "keys": list(value.keys())}
        for key in ("result", "itineraries", "outbound", "inbound", "segments"):
            if key in value:
                summary[key] = _shape_summary(value[key])
        return summary

    if isinstance(value, list):
        first = value[0] if value else None
        return {
            "type": "list",
            "length": len(value),
            "first_item": _shape_summary(first),
        }

    return {"type": type(value).__name__}


def _json_safe(value: Any) -> Any:
    """Convert common Python objects into JSON-serializable values."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


if __name__ == "__main__":
    asyncio.run(main())
