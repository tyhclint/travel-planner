import os
from functools import lru_cache
from typing import Final

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

KIWI_MCP_SERVER_NAME: Final = "kiwi"
KIWI_MCP_DEFAULT_URL: Final = "https://mcp.kiwi.com"


@lru_cache
def get_flight_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {
            KIWI_MCP_SERVER_NAME: {
                "transport": "streamable_http",
                "url": os.getenv("KIWI_MCP_URL", KIWI_MCP_DEFAULT_URL),
            }
        },
        tool_name_prefix=True,
    )


async def get_flight_mcp_tools() -> list[BaseTool]:
    client = get_flight_mcp_client()
    return await client.get_tools(server_name=KIWI_MCP_SERVER_NAME)
