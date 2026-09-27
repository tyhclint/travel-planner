import json
from typing import Any


def json_value(value: Any) -> str:
    """Serialize prompt values to JSON strings, including Pydantic models."""
    if value is None:
        return "null"
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json()
    if isinstance(value, list):
        return json.dumps([_json_safe(item) for item in value], default=str)
    return json.dumps(_json_safe(value), default=str)


def _json_safe(value: Any) -> Any:
    """Convert Pydantic values into structures json.dumps can handle."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value
