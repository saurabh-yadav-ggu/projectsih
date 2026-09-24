import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.agent.subagents.chat_agent import run_chat_agent
from app.agent.subagents.document_agent import run_document_agent
from app.agent.subagents.rag_agent import run_rag_agent
from app.agent.subagents.vision_agent import run_vision_agent
from app.agent.subagents.coding_agent import run_coding_agent
from app.backends.filesystem import FilesystemBackend

logger = logging.getLogger("app.agent.delegation")


async def delegate_task(
    intent: str,
    query: str,
    user_id: Optional[int] = None,
    thread_id: Optional[str] = None,
    memory_context: str = "",
    document_context: str = "",
    image_path: Optional[str] = None,
    fs_backend: Optional[FilesystemBackend] = None,
) -> Dict[str, Any]:
    """
    Dispatches task to the appropriate specialized subagent and returns the structured result.
    """
    logger.info(f"Delegating task with intent '{intent}' for user {user_id}, thread {thread_id}")

    if intent == "document":
        return await run_document_agent(
            query=query,
            user_id=user_id,
            thread_id=thread_id,
            fs_backend=fs_backend,
            document_context=document_context,
        )
    elif intent == "rag":
        return await run_rag_agent(
            query=query,
            thread_id=thread_id,
            user_id=user_id,
            document_context=document_context,
        )
    elif intent == "vision" and image_path:
        return await run_vision_agent(
            image_path=image_path,
            question=query,
        )
    elif intent == "coding":
        ws = fs_backend.get_user_workspace(user_id) if (fs_backend and user_id) else Path("./workspace")
        return await run_coding_agent(
            task_description=query,
            workspace_path=ws,
        )
    else:
        # Default: Chat Agent
        return await run_chat_agent(
            query=query,
            memory_context=memory_context,
            document_context=document_context,
        )
