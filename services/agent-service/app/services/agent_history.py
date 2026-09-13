from typing import Any

from langchain_core.messages import ToolMessage


def agent_tool_history(messages: list[Any], tool_names: set[str]) -> list[Any]:
    """Keep prior agent AI/tool messages in order so tool-call IDs stay paired."""
    history: list[Any] = []
    for message in messages:
        if known_tool_calls(getattr(message, "tool_calls", []) or [], tool_names) or (
            isinstance(message, ToolMessage) and message.name in tool_names
        ):
            history.append(message)
    return history


def known_tool_calls(
    tool_calls: list[dict[str, Any]],
    tool_names: set[str],
) -> list[dict[str, Any]]:
    """Return only tool calls that belong to the provided tool-name set."""
    return [call for call in tool_calls if call.get("name") in tool_names]
