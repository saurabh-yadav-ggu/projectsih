import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.repositories import ThreadRepository, MessageRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.agent import run_agent_query
from app.rag import retrieve_context
from app.memory import (
    format_memories_for_prompt,
    extract_and_save_memories,
    generate_and_save_title
)

logger = logging.getLogger("app.routers.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Obtain or create thread with ownership verification
    if body.thread_id:
        thread = ThreadRepository.get_thread(db, thread_id=body.thread_id, user_id=current_user.id)
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or access denied"
            )
    else:
        thread = ThreadRepository.create_thread(db, user_id=current_user.id)

    # 2. Persist user message to SQLite
    MessageRepository.add_message(
        db,
        thread_id=thread.id,
        role="user",
        content=body.message
    )
    ThreadRepository.touch_thread(db, thread_id=thread.id, user_id=current_user.id)

    # 3. Retrieve user memory context & thread document context
    memory_context = format_memories_for_prompt(db, user_id=current_user.id)
    document_context = retrieve_context(query=body.message, k=6, thread_id=thread.id)

    # 4. Invoke LangGraph ReAct Agent with AsyncSqliteSaver checkpointer
    try:
        response_content = await run_agent_query(
            message=body.message,
            thread_id=thread.id,
            memory_context=memory_context,
            document_context=document_context
        )
    except Exception as e:
        logger.error(f"Error during agent execution: {e}")
        response_content = f"An error occurred while processing your request: {str(e)}"

    # 5. Persist assistant response to SQLite
    MessageRepository.add_message(
        db,
        thread_id=thread.id,
        role="assistant",
        content=response_content
    )

    # 6. Schedule automated title generation and memory extraction as background tasks
    background_tasks.add_task(
        generate_and_save_title,
        db=db,
        thread_id=thread.id,
        user_id=current_user.id,
        user_message=body.message
    )
    background_tasks.add_task(
        extract_and_save_memories,
        db=db,
        user_id=current_user.id,
        user_message=body.message
    )

    # Fetch updated thread title if changed
    updated_thread = ThreadRepository.get_thread(db, thread_id=thread.id, user_id=current_user.id)
    title = updated_thread.title if updated_thread else thread.title

    return ChatResponse(
        thread_id=thread.id,
        message=response_content,
        title=title
    )
