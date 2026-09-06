import asyncio
import os
import sys
from pathlib import Path
from typing import Tuple, List, Optional
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

# Base workspace directory and output directory for docgen
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "out"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _get_docgen_command_and_args() -> Tuple[str, List[str]]:
    """Determine the fastest and most reliable command to start mcp-docgen server."""
    # 1. Check if mcp_docgen is installed in current Python environment
    try:
        import mcp_docgen  # noqa: F401
        return sys.executable, ["-m", "mcp_docgen.server"]
    except ImportError:
        pass

    # 2. Check for mcp-docgen executable in current Python environment Scripts
    exe = Path(sys.executable).parent / "mcp-docgen.exe"
    if exe.exists():
        return str(exe), []

    # 3. Fallback to uvx
    return "uvx", ["--with", "mcp<2", "mcp-docgen"]


_cmd, _args = _get_docgen_command_and_args()

# Configuration for MCP servers
MCP_SERVERS = {
    "docgen": {
        "transport": "stdio",
        "command": _cmd,
        "args": _args,
        "env": {
            "MCP_DOCGEN_OUTPUT_DIR": str(OUTPUT_DIR),
            "MCP_DOCGEN_INPUT_DIR": str(OUTPUT_DIR),
        },
    }
}

_mcp_client: Optional[MultiServerMCPClient] = None
_mcp_tools: Optional[List[BaseTool]] = None


def get_mcp_client() -> MultiServerMCPClient:
    """Instantiate and return the MultiServerMCPClient."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MultiServerMCPClient(MCP_SERVERS)
    return _mcp_client


async def get_mcp_tools() -> Tuple[List[BaseTool], MultiServerMCPClient]:
    """Connect to configured MCP servers and retrieve available tools."""
    global _mcp_tools
    client = get_mcp_client()
    if _mcp_tools is None:
        raw_tools = await client.get_tools()
        # Sanitize all tool descriptions: strip all newlines and multiple spaces
        sanitized_tools = []
        for tool in raw_tools:
            if tool.description:
                tool.description = " ".join(tool.description.split())
            sanitized_tools.append(tool)
        _mcp_tools = sanitized_tools
    return _mcp_tools, client


async def main():
    print(f"Connecting to MCP server (output dir: {OUTPUT_DIR})...")
    tools, _ = await get_mcp_tools()
    print(f"Successfully loaded {len(tools)} tools from MCP:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description.splitlines()[0] if tool.description else ''}")


if __name__ == "__main__":
    asyncio.run(main())
