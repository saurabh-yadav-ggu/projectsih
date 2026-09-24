import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger("app.mcp")

BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "out"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
MCP_CONFIG_PATHS = [
    ROOT_DIR / "mcp.json",
    Path(__file__).resolve().parent.parent.parent / "mcp.json",
]


def load_mcp_servers_config() -> Dict[str, Any]:
    """
    Dynamically loads MCP server definitions from mcp.json or environment,
    with automatic discovery of local services without hardcoded bindings.
    """
    servers: Dict[str, Any] = {}

    # 1. Try reading from mcp.json files
    for config_path in MCP_CONFIG_PATHS:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    mcp_servers = data.get("mcpServers", {})
                    for name, s_cfg in mcp_servers.items():
                        # Normalize config format for MultiServerMCPClient
                        if "command" in s_cfg:
                            servers[name] = {
                                "transport": s_cfg.get("transport", "stdio"),
                                "command": s_cfg["command"],
                                "args": s_cfg.get("args", []),
                                "env": s_cfg.get("env", {}),
                            }
                        elif "url" in s_cfg:
                            servers[name] = {
                                "transport": "sse",
                                "url": s_cfg["url"],
                                "headers": s_cfg.get("headers", {}),
                            }
            except Exception as e:
                logger.warning(f"Error reading MCP config from {config_path}: {e}")

    # 2. Dynamic discovery of docgen if installed in environment
    if "docgen" not in servers:
        try:
            import mcp_docgen
            servers["docgen"] = {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "mcp_docgen.server"],
                "env": {
                    "MCP_DOCGEN_OUTPUT_DIR": str(OUTPUT_DIR),
                    "MCP_DOCGEN_INPUT_DIR": str(OUTPUT_DIR),
                },
            }
        except ImportError:
            pass

    return servers


_mcp_client: Optional[MultiServerMCPClient] = None
_mcp_tools: Optional[List[BaseTool]] = None


def get_mcp_client() -> Optional[MultiServerMCPClient]:
    """Instantiate and return the MultiServerMCPClient dynamically."""
    global _mcp_client
    if _mcp_client is None:
        servers = load_mcp_servers_config()
        if servers:
            try:
                _mcp_client = MultiServerMCPClient(servers)
            except Exception as e:
                logger.error(f"Failed to initialize MultiServerMCPClient: {e}")
                return None
    return _mcp_client


async def get_mcp_tools() -> Tuple[List[BaseTool], Optional[MultiServerMCPClient]]:
    """
    Connect to dynamically configured MCP servers and retrieve available tools.
    Sanitizes all tool descriptions to eliminate Ollama newline parsing errors.
    """
    global _mcp_tools
    client = get_mcp_client()
    if client is None:
        return [], None

    if _mcp_tools is None:
        try:
            raw_tools = await client.get_tools()
            sanitized_tools = []
            for tool in raw_tools:
                if tool.description:
                    # Sanitize all newlines and multiple spaces for safe LLM JSON serializing
                    tool.description = " ".join(tool.description.split())
                sanitized_tools.append(tool)
            _mcp_tools = sanitized_tools
        except Exception as e:
            logger.warning(f"Unable to fetch MCP tools: {e}")
            _mcp_tools = []

    return _mcp_tools, client


async def main():
    print(f"Connecting to dynamically discovered MCP servers...")
    tools, _ = await get_mcp_tools()
    print(f"Loaded {len(tools)} tools dynamically from MCP:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")


if __name__ == "__main__":
    asyncio.run(main())
