import json
import re
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlparse

from langchain_core.messages import ToolMessage
from pydantic import ValidationError

from app.domain.models.accommodations import AccommodationOption


def parse_accommodation_tool_messages(
    accommodation_tool_messages: list[ToolMessage],
) -> list[AccommodationOption]:
    """Parse accommodation ToolMessages into deduplicated AccommodationOption objects."""
    candidate_records: dict[str, dict[str, Any]] = {}
    search_dates: dict[str, date | None] = {"check_in": None, "check_out": None}

    for message in accommodation_tool_messages:
        payload = _load_tool_payload(message)
        if not isinstance(payload, dict):
            continue

        if message.name == "search_accommodations":
            _merge_search_results(payload, candidate_records, search_dates)
        elif message.name == "get_accommodation_details":
            _merge_hotel_payload(payload, candidate_records)
        elif message.name == "get_accommodation_reviews":
            _merge_review_payload(payload, candidate_records)

    options: list[AccommodationOption] = []
    for record in candidate_records.values():
        option = _record_to_accommodation_option(record, search_dates)
        if option is not None:
            options.append(option)

    return options


def _load_tool_payload(message: ToolMessage) -> Any:
    """Extract structured payload data from a LangChain ToolMessage."""
    artifact = getattr(message, "artifact", None)
    if artifact:
        return artifact.get("structured_content", artifact)

    if isinstance(message.content, str):
        try:
            return json.loads(message.content)
        except json.JSONDecodeError:
            return {}

    return message.content


def _merge_search_results(
    payload: dict[str, Any],
    candidate_records: dict[str, dict[str, Any]],
    search_dates: dict[str, date | None],
) -> None:
    result = payload.get("result", {})
    if isinstance(result, list):
        _merge_search_text_blocks(result, candidate_records, search_dates)
        return

    if not isinstance(result, dict):
        return

    search_dates["check_in"] = search_dates["check_in"] or _parse_date(
        _first_present(result, "checkIn", "checkin", "check_in")
    )
    search_dates["check_out"] = search_dates["check_out"] or _parse_date(
        _first_present(result, "checkOut", "checkout", "check_out")
    )

    for hotel in _hotel_items(result):
        hotel_id = _hotel_id(hotel)
        if hotel_id is None:
            continue
        record = candidate_records.setdefault(hotel_id, {})
        record.update(_flatten_hotel_record(hotel))
        record["id"] = hotel_id


def _merge_hotel_payload(
    payload: dict[str, Any],
    candidate_records: dict[str, dict[str, Any]],
) -> None:
    result = payload.get("result", {})
    if isinstance(result, list):
        _merge_review_text_blocks(result, payload, candidate_records)
        return

    if not isinstance(result, dict):
        return

    hotel = _first_hotel_object(result)
    hotel_id = _hotel_id(hotel) or _string(payload.get("hotel_id"))
    if hotel_id is None:
        return

    record = candidate_records.setdefault(hotel_id, {})
    record.update(_flatten_hotel_record(hotel))
    record["id"] = hotel_id


def _merge_review_payload(
    payload: dict[str, Any],
    candidate_records: dict[str, dict[str, Any]],
) -> None:
    result = payload.get("result", {})
    if not isinstance(result, dict):
        return

    hotel_id = _string(payload.get("hotel_id")) or _string(
        _first_present(result, "hotelId", "hotel_id", "id")
    )
    if hotel_id is None:
        return

    record = candidate_records.setdefault(hotel_id, {"id": hotel_id})
    review_summary = _first_present(result, "summary", "sentimentSummary", "reviewSummary")
    rating = _number(_first_present(result, "rating", "averageRating", "reviewScore"))
    if review_summary:
        record["review_summary"] = str(review_summary)
    if rating is not None and record.get("rating") is None:
        record["rating"] = rating


def _merge_search_text_blocks(
    result: list[Any],
    candidate_records: dict[str, dict[str, Any]],
    search_dates: dict[str, date | None],
) -> None:
    """Parse MoodTrip markdown search result blocks into hotel candidate records."""
    for block in result:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = _string(block.get("text"))
        if text is None:
            continue
        for hotel in _parse_search_markdown(text):
            hotel_id = _string(hotel.get("id"))
            if hotel_id is None:
                continue
            record = candidate_records.setdefault(hotel_id, {})
            record.update(hotel)
            record["id"] = hotel_id
            if search_dates["check_in"] is None:
                search_dates["check_in"] = _parse_date(hotel.get("check_in"))
            if search_dates["check_out"] is None:
                search_dates["check_out"] = _parse_date(hotel.get("check_out"))


def _merge_review_text_blocks(
    result: list[Any],
    payload: dict[str, Any],
    candidate_records: dict[str, dict[str, Any]],
) -> None:
    """Attach MoodTrip review markdown to the matching hotel candidate record."""
    hotel_id = _string(payload.get("hotel_id"))
    if hotel_id is None:
        return

    texts = [
        str(block.get("text"))
        for block in result
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
    ]
    if not texts:
        return

    record = candidate_records.setdefault(hotel_id, {"id": hotel_id})
    record["review_summary"] = "\n\n".join(texts)


def _parse_search_markdown(text: str) -> list[dict[str, Any]]:
    """Extract hotel candidates from MoodTrip's markdown search output."""
    city = _search_city(text)
    hotels: list[dict[str, Any]] = []
    lines = text.splitlines()

    for index, line in enumerate(lines):
        hotel_match = re.match(
            r"^\*\*(?P<name>.+?)\*\*\s+⭐\s*(?P<rating>\d+(?:\.\d+)?)/10\s*\|?\s*"
            r"\*\*(?P<currency>[A-Z]{3})\s+(?P<price>\d+(?:\.\d+)?)\*\*/night",
            line.strip(),
        )
        if hotel_match is None:
            continue

        moodtrip_rating = _number(hotel_match.group("rating"))
        record: dict[str, Any] = {
            "name": hotel_match.group("name"),
            "rating": moodtrip_rating / 2 if moodtrip_rating is not None else None,
            "nightly_price": _number(hotel_match.group("price")),
            "total_price": _number(hotel_match.group("price")),
            "currency": hotel_match.group("currency"),
            "location": city,
        }

        for nearby_line in lines[index + 1 : index + 5]:
            if nearby_line.startswith("!["):
                image_match = re.search(r"\]\((?P<url>https?://[^)]+)\)", nearby_line)
                if image_match:
                    record["image_url"] = image_match.group("url")
            if "[View & Book]" in nearby_line:
                url = _markdown_url(nearby_line)
                if url:
                    record["booking_url"] = url
                    record["id"] = _hotel_id_from_url(url)
                    record.update(_dates_from_url(url))
            if "[View Gallery]" in nearby_line:
                url = _markdown_url(nearby_line)
                if url:
                    record["gallery_url"] = url

        hotels.append(record)

    return hotels


def _search_city(text: str) -> str | None:
    match = re.search(r"Found \*\*\d+ hotels\*\* in \*\*(?P<city>.+?)\*\*", text)
    if match:
        return match.group("city")
    return None


def _markdown_url(line: str) -> str | None:
    match = re.search(r"\]\((?P<url>https?://[^)]+)\)", line)
    if match:
        return match.group("url")
    return None


def _hotel_id_from_url(url: str) -> str | None:
    match = re.search(r"/hotel/(?P<hotel_id>[^?\s/]+)", url)
    if match:
        return match.group("hotel_id")
    return None


def _dates_from_url(url: str) -> dict[str, str]:
    query = parse_qs(urlparse(url).query)
    dates = {}
    if query.get("checkin"):
        dates["check_in"] = query["checkin"][0]
    if query.get("checkout"):
        dates["check_out"] = query["checkout"][0]
    return dates


def _record_to_accommodation_option(
    record: dict[str, Any],
    search_dates: dict[str, date | None],
) -> AccommodationOption | None:
    nightly_price = _number(
        _first_present(record, "nightly_price", "nightlyPrice", "pricePerNight", "rate")
    )
    total_price = _number(_first_present(record, "total_price", "totalPrice", "price", "amount"))
    if nightly_price is None and total_price is not None:
        nightly_price = total_price
    if total_price is None and nightly_price is not None:
        total_price = nightly_price

    hotel_id = _string(record.get("id"))
    name = _string(_first_present(record, "name", "hotelName", "title"))
    location = _string(_first_present(record, "location", "address", "city", "destination"))
    if hotel_id is None or name is None or location is None or nightly_price is None or total_price is None:
        return None

    try:
        return AccommodationOption(
            id=hotel_id,
            name=name,
            accommodation_type=_string(record.get("accommodation_type")) or "hotel",
            location=location,
            latitude=_number(_first_present(record, "latitude", "lat")),
            longitude=_number(_first_present(record, "longitude", "lng", "lon")),
            check_in=_parse_date(_first_present(record, "check_in", "checkIn", "checkin"))
            or search_dates["check_in"],
            check_out=_parse_date(_first_present(record, "check_out", "checkOut", "checkout"))
            or search_dates["check_out"],
            rating=_number(_first_present(record, "rating", "stars", "starRating", "reviewScore")),
            nightly_price=float(nightly_price),
            total_price=float(total_price),
            currency=(
                _string(_first_present(record, "currency", "currencyCode")) or "USD"
            ).upper(),
            amenities=_string_list(_first_present(record, "amenities", "facilities")),
            provider="moodtrip",
            booking_url=_string(_first_present(record, "booking_url", "bookingUrl", "url")),
        )
    except (TypeError, ValueError, ValidationError):
        return None


def _hotel_items(result: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("hotels", "results", "data", "items"):
        value = result.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    hotel = _first_hotel_object(result)
    return [hotel] if hotel else []


def _first_hotel_object(result: dict[str, Any]) -> dict[str, Any]:
    for key in ("hotel", "details", "data", "result"):
        value = result.get(key)
        if isinstance(value, dict):
            return value
    return result


def _flatten_hotel_record(hotel: dict[str, Any]) -> dict[str, Any]:
    record = dict(hotel)
    price = hotel.get("price")
    if isinstance(price, dict):
        for source, target in (
            ("nightly", "nightly_price"),
            ("nightlyPrice", "nightly_price"),
            ("perNight", "nightly_price"),
            ("total", "total_price"),
            ("totalPrice", "total_price"),
            ("amount", "total_price"),
            ("currency", "currency"),
        ):
            if source in price and target not in record:
                record[target] = price[source]

    rates = hotel.get("rates")
    if isinstance(rates, list) and rates:
        first_rate = rates[0]
        if isinstance(first_rate, dict):
            for key, value in first_rate.items():
                record.setdefault(key, value)

    return record


def _hotel_id(hotel: dict[str, Any]) -> str | None:
    return _string(_first_present(hotel, "id", "hotelId", "hotel_id", "liteapiHotelId"))


def _first_present(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return None


def _string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        return None

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]
