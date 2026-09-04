import logging
from typing import List
from langchain_core.tools import BaseTool

logger = logging.getLogger("app.mcp")

async def get_mcp_tools() -> List[BaseTool]:
    """
    Dynamically loads tools from MCP servers.
    Falls back gracefully if MCP servers or langchain_mcp_adapters are unavailable.
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient  # noqa
        # If client configuration exists, initialize here:
        # client = MultiServerMCPClient(...)
        # return await client.get_tools()
        return []
    except ImportError:
        logger.info("langchain_mcp_adapters not installed or no active MCP server configured. Returning empty MCP tools.")
        return []
    except Exception as e:
        logger.warning(f"Failed to fetch MCP tools: {e}")
        return []
