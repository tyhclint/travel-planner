"""Inspect raw payloads returned by MoodTrip MCP accommodation tools.

Run from services/agent-service:
    python -m app.scripts.inspect_moodtrip_payload

The script calls searchHotelsWithRates first, extracts a hotel ID, then calls
getHotelReviews with that ID. Use --hotel-id to skip automatic ID extraction.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import ToolMessage

from app.services.accommodations.mcp import get_accommodation_mcp_tools

DEFAULT_SEARCH_OUTPUT_PATH = Path("app/scripts/moodtrip_search_hotels_payload_sample.json")
DEFAULT_REVIEWS_OUTPUT_PATH = Path("app/scripts/moodtrip_hotel_reviews_payload_sample.json")


def parse_args() -> argparse.Namespace:
    """Parse CLI options for sample MoodTrip accommodation calls."""
    parser = argparse.ArgumentParser(
        description="Call MoodTrip MCP hotel tools and inspect their payload shapes."
    )
    parser.add_argument("--city-name", default="Tokyo")
    parser.add_argument("--country-code", default="JP")
    parser.add_argument("--place-id", default=None)
    parser.add_argument("--checkin", default="2026-11-10")
    parser.add_argument("--checkout", default="2026-11-14")
    parser.add_argument(
        "--occupancies",
        default='[{"adults": 2, "children": []}]',
        help="JSON array matching MoodTrip occupancies input.",
    )
    parser.add_argument("--hotel-name", default=None)
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--guest-nationality", default=None)
    parser.add_argument("--max-price", type=float, default=None)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument(
        "--hotel-id",
        default=None,
        help="Hotel ID for getHotelReviews. If omitted, extract one from search results.",
    )
    parser.add_argument("--get-sentiment", action="store_true")
    parser.add_argument(
        "--search-output",
        type=Path,
        default=DEFAULT_SEARCH_OUTPUT_PATH,
        help="Where to write the extracted searchHotelsWithRates payload JSON.",
    )
    parser.add_argument(
        "--reviews-output",
        type=Path,
        default=DEFAULT_REVIEWS_OUTPUT_PATH,
        help="Where to write the extracted getHotelReviews payload JSON.",
    )
    parser.add_argument(
        "--print-limit",
        type=int,
        default=6000,
        help="Max characters of each extracted payload JSON to print.",
    )
    return parser.parse_args()


async def main() -> None:
    """Call MoodTrip search and reviews tools, then save raw extracted payloads."""
    _configure_utf8_output()
    args = parse_args()

    search_tool = await _moodtrip_tool("searchHotelsWithRates")
    reviews_tool = await _moodtrip_tool("getHotelReviews")

    search_args = _search_tool_args(args)
    print(f"Search tool name: {search_tool.name}")
    print(f"Search tool args: {json.dumps(search_args, indent=2)}")

    raw_search_result = await search_tool.ainvoke(search_args)
    search_payload = _extract_payload(raw_search_result)
    _save_payload(args.search_output, search_payload)

    print_payload_report(
        title="searchHotelsWithRates",
        raw_result=raw_search_result,
        payload=search_payload,
        output_path=args.search_output,
        print_limit=args.print_limit,
    )

    hotel_id = args.hotel_id or _first_hotel_id(search_payload)
    if not hotel_id:
        raise RuntimeError(
            "Could not find a hotel ID in searchHotelsWithRates payload. "
            "Re-run with --hotel-id after inspecting the saved search payload."
        )

    reviews_args = {
        "hotelId": hotel_id,
        "getSentiment": bool(args.get_sentiment),
    }
    print(f"\nReviews tool name: {reviews_tool.name}")
    print(f"Reviews tool args: {json.dumps(reviews_args, indent=2)}")

    raw_reviews_result = await reviews_tool.ainvoke(reviews_args)
    reviews_payload = _extract_payload(raw_reviews_result)
    _save_payload(args.reviews_output, reviews_payload)

    print_payload_report(
        title="getHotelReviews",
        raw_result=raw_reviews_result,
        payload=reviews_payload,
        output_path=args.reviews_output,
        print_limit=args.print_limit,
    )


async def _moodtrip_tool(tool_name: str):
    """Load a MoodTrip MCP tool by provider name, with or without client prefix."""
    tools = await get_accommodation_mcp_tools()
    expected_names = {tool_name, f"moodtrip_{tool_name}"}
    for tool in tools:
        if tool.name in expected_names:
            return tool

    available = ", ".join(tool.name for tool in tools)
    raise RuntimeError(f"{tool_name} not found. Available tools: {available}")


def _search_tool_args(args: argparse.Namespace) -> dict[str, Any]:
    """Build raw searchHotelsWithRates MCP args from CLI options."""
    occupancies = json.loads(args.occupancies)
    if not isinstance(occupancies, list):
        raise TypeError("--occupancies must be a JSON array.")

    tool_args: dict[str, Any] = {
        "checkin": args.checkin,
        "checkout": args.checkout,
        "occupancies": occupancies,
        "currency": args.currency.upper(),
    }
    if args.city_name:
        tool_args["cityName"] = args.city_name
    if args.country_code:
        tool_args["countryCode"] = args.country_code.upper()
    if args.place_id:
        tool_args["placeId"] = args.place_id
    if args.hotel_name:
        tool_args["hotelName"] = args.hotel_name
    if args.guest_nationality:
        tool_args["guestNationality"] = args.guest_nationality.upper()
    if args.max_price is not None:
        tool_args["maxPrice"] = args.max_price
    if args.limit is not None:
        tool_args["limit"] = args.limit
    return tool_args


def _extract_payload(raw_result: Any) -> Any:
    """Remove LangChain wrapper data so the MCP payload can be inspected directly."""
    if isinstance(raw_result, ToolMessage):
        artifact = getattr(raw_result, "artifact", None)
        if isinstance(artifact, dict):
            return artifact.get("structured_content", artifact)
        return _json_payload(raw_result.content)

    if isinstance(raw_result, tuple) and len(raw_result) == 2:
        content, artifact = raw_result
        if isinstance(artifact, dict):
            return artifact.get("structured_content", artifact)
        return _json_payload(content)

    return _json_payload(raw_result)


def _json_payload(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _first_hotel_id(value: Any) -> str | None:
    """Find the first plausible hotel ID in a provider payload."""
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            candidate = _hotel_id_from_text(text)
            if candidate:
                return candidate

        for key in ("hotelId", "hotel_id", "liteapiHotelId"):
            candidate = value.get(key)
            if candidate:
                return str(candidate)

        candidate = value.get("id")
        if candidate and not str(candidate).startswith("lc_"):
            return str(candidate)

        for item in value.values():
            candidate = _first_hotel_id(item)
            if candidate:
                return candidate

    if isinstance(value, list):
        for item in value:
            candidate = _first_hotel_id(item)
            if candidate:
                return candidate

    return None


def _hotel_id_from_text(text: str) -> str | None:
    """Extract a MoodTrip/LiteAPI hotel ID from markdown links in text content."""
    match = re.search(r"moodtrip\.ai/hotel/([^?\s)\]]+)", text)
    if match:
        return match.group(1)
    return None


def print_payload_report(
    *,
    title: str,
    raw_result: Any,
    payload: Any,
    output_path: Path,
    print_limit: int,
) -> None:
    """Print response type, structural summary, save path, and payload preview."""
    payload_json = json.dumps(_json_safe(payload), indent=2, default=str)
    print(f"\n{title} raw result type: {type(raw_result).__name__}")
    print(f"{title} extracted payload type: {type(payload).__name__}")
    print(f"{title} shape summary:")
    print(json.dumps(_shape_summary(payload), indent=2, default=str))
    print(f"\nSaved {title} payload to: {output_path}")
    print(f"\n{title} payload preview:")
    print(payload_json[:print_limit])
    if len(payload_json) > print_limit:
        print(f"\n... truncated at {print_limit} characters")


def _save_payload(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, default=str),
        encoding="utf-8",
    )


def _shape_summary(value: Any) -> Any:
    """Create a compact structural summary of nested dict/list payload data."""
    if isinstance(value, dict):
        summary: dict[str, Any] = {"type": "dict", "keys": list(value.keys())}
        for key in (
            "result",
            "data",
            "hotels",
            "hotel",
            "rates",
            "reviews",
            "sentiment",
        ):
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
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def _configure_utf8_output() -> None:
    """Use UTF-8 when printing redirected output on Windows terminals."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
