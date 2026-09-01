"""Minimal JSON-RPC stdio server for MCP-capable clients."""

import json
import sys
from typing import Any

from app.services.mcp.registry import get_local_registry


def _send(request_id: Any, result: dict[str, Any]) -> None:
    payload = json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})
    encoded = payload.encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def main() -> None:
    registry = get_local_registry()
    while True:
        headers: dict[str, str] = {}
        line = sys.stdin.buffer.readline()
        if not line:
            return
        while line not in (b"\r\n", b"\n", b""):
            key, _, value = line.decode("ascii").partition(":")
            headers[key.lower().strip()] = value.strip()
            line = sys.stdin.buffer.readline()
        length = int(headers.get("content-length", "0"))
        request = json.loads(sys.stdin.buffer.read(length))
        request_id = request.get("id")
        if request_id is None:
            continue
        method = request.get("method")
        if method == "initialize":
            _send(request_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "travel-planner", "version": "0.1.0"}})
        elif method == "tools/list":
            _send(request_id, {"tools": registry.list_tools()})
        elif method == "tools/call":
            params = request.get("params", {})
            try:
                value = registry.call_tool(params["name"], params.get("arguments", {}))
                _send(request_id, {"content": [{"type": "text", "text": json.dumps(value)}], "isError": False})
            except (KeyError, TypeError, ValueError) as exc:
                _send(request_id, {"content": [{"type": "text", "text": str(exc)}], "isError": True})
        else:
            _send(request_id, {"error": f"Unsupported method: {method}"})


if __name__ == "__main__":
    main()
