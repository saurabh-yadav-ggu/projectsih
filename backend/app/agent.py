"""
Backward-compatibility layer for app.agent.
Delegates to the Deep Agent supervisor in app.agent.main_agent while preserving
legacy function signatures and constants.
"""
from app.agent.main_agent import (
    run_supervisor_agent,
    run_agent_query,
    stream_agent_query,
    supervisor_agent,
)
from app.agent.state import DeepAgentState
from app.mcp import OUTPUT_DIR
from app.config import settings

__all__ = [
    "run_supervisor_agent",
    "run_agent_query",
    "stream_agent_query",
    "supervisor_agent",
    "DeepAgentState",
    "OUTPUT_DIR",
    "settings",
]