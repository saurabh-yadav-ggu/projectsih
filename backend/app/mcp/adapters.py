from typing import List, Optional
from langchain_core.tools import BaseTool

from app.mcp.mcp_client import get_mcp_tools


async def get_tools_for_subagent(allowed_names: Optional[List[str]] = None) -> List[BaseTool]:
    """
    Returns dynamically loaded MCP tools, optionally filtered by tool names.
    """
    tools, _ = await get_mcp_tools()
    if not allowed_names:
        return tools
    return [t for t in tools if t.name in allowed_names]
