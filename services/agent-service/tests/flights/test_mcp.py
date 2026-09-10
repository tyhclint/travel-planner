from app.services.flights import mcp


def test_flight_mcp_client_uses_default_kiwi_connection(monkeypatch):
    monkeypatch.delenv("KIWI_MCP_URL", raising=False)
    mcp.get_flight_mcp_client.cache_clear()

    client = mcp.get_flight_mcp_client()
    connection = client.connections[mcp.KIWI_MCP_SERVER_NAME]

    assert connection["transport"] == "streamable_http"
    assert connection["url"] == mcp.KIWI_MCP_DEFAULT_URL


def test_flight_mcp_client_allows_kiwi_url_override(monkeypatch):
    monkeypatch.setenv("KIWI_MCP_URL", "https://example.test/mcp")
    mcp.get_flight_mcp_client.cache_clear()

    client = mcp.get_flight_mcp_client()
    connection = client.connections[mcp.KIWI_MCP_SERVER_NAME]

    assert connection["url"] == "https://example.test/mcp"

    mcp.get_flight_mcp_client.cache_clear()
