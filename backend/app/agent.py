import json
import logging
from pathlib import Path
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import settings
from app.tools import local_tools
from app.mcp import get_mcp_tools

logger = logging.getLogger("app.agent")

PROMPT_PATH = Path(__file__).resolve().parent / "prompt.json"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_DB_PATH = DATA_DIR / "checkpoints.db"


def get_base_system_prompt() -> str:
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("system_prompt", "You are ShieldAi assistant.")
    except Exception as e:
        logger.error(f"Failed to load prompt.json: {e}")
        return "You are a helpful AI assistant."


async def run_agent_query(message: str, thread_id: str, memory_context: str = "") -> str:
    """
    Executes the LangGraph ReAct agent query using AsyncSqliteSaver context manager.
    """
    from langchain_core.messages import HumanMessage

    mcp_tools = await get_mcp_tools()
    all_tools = [*local_tools, *mcp_tools]

    base_prompt = get_base_system_prompt()
    full_prompt = f"{base_prompt}\n{memory_context}" if memory_context else base_prompt

    llm = ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
    )

    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH)) as checkpointer:
        agent = create_react_agent(
            model=llm,
            tools=all_tools,
            prompt=full_prompt,
            checkpointer=checkpointer,
        )

        inputs = {"messages": [HumanMessage(content=message)]}
        config = {"configurable": {"thread_id": thread_id}}

        result = await agent.ainvoke(inputs, config=config)

        messages = result.get("messages", [])
        if messages:
            return str(messages[-1].content)
        return "I processed your request, but generated no output text."