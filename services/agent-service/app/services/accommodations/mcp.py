import os
from functools import lru_cache
from typing import Final

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

MOODTRIP_MCP_SERVER_NAME: Final = "moodtrip"
MOODTRIP_MCP_DEFAULT_URL: Final = "https://api.moodtrip.ai/api/mcp-http"


@lru_cache
def get_accommodation_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {
            MOODTRIP_MCP_SERVER_NAME: {
                "transport": "streamable_http",
                "url": os.getenv("MOODTRIP_MCP_URL", MOODTRIP_MCP_DEFAULT_URL),
            }
        },
        tool_name_prefix=True,
    )


async def get_accommodation_mcp_tools() -> list[BaseTool]:
    client = get_accommodation_mcp_client()
    return await client.get_tools(server_name=MOODTRIP_MCP_SERVER_NAME)
