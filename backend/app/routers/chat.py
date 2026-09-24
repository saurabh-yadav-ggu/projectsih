import json
import logging
import re
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.repositories import ThreadRepository, MessageRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.agent import run_agent_query, stream_agent_query
from app.rag import retrieve_context
from app.memory import (
    format_memories_for_prompt,
    extract_and_save_memories,
    generate_and_save_title
)

logger = logging.getLogger("app.routers.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _resolve_image_path(explicit_path: Optional[str], message: str) -> Optional[str]:
    """
    Resolves image path strictly.
    1. Returns explicit_path if provided and valid.
    2. Only falls back to recent upload if the user explicitly asks to analyze/describe an image.
    """
    if explicit_path and Path(explicit_path).exists():
        return explicit_path

    q = message.lower()
    has_image_term = bool(re.search(r"\b(image|photo|picture|screenshot|diagram)\b", q))
    has_inspect_term = bool(re.search(r"\b(describe|analyze|inspect|read|what is in|tell me about|extract)\b", q))
    if has_image_term and has_inspect_term:
        upload_dir = Path(__file__).resolve().parents[2] / "uploads"
        if upload_dir.exists():
            img_candidates = sorted(
                [f for f in upload_dir.iterdir() if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]],
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            if img_candidates:
                return str(img_candidates[0].resolve())
    return None


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

    # 3. Retrieve user memory context & thread document context with user isolation
    memory_context = format_memories_for_prompt(db, user_id=current_user.id)
    document_context = retrieve_context(query=body.message, k=6, thread_id=thread.id, user_id=current_user.id)

    # 4. Resolve image context if provided or explicitly requested
    image_path = _resolve_image_path(body.image_path, body.message)

    # 5. Invoke Supervisor Deep Agent
    try:
        response_content = await run_agent_query(
            message=body.message,
            thread_id=thread.id,
            memory_context=memory_context,
            document_context=document_context,
            user_id=current_user.id,
            image_path=image_path,
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


@router.post("/stream")
async def chat_stream_endpoint(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Obtain or create thread
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

    # 3. Context retrieval with user isolation
    memory_context = format_memories_for_prompt(db, user_id=current_user.id)
    document_context = retrieve_context(query=body.message, k=6, thread_id=thread.id, user_id=current_user.id)

    # 4. Resolve image context if provided or explicitly requested
    stream_image_path = _resolve_image_path(body.image_path, body.message)

    async def event_generator():
        accumulated_text = ""
        try:
            # Yield initial thread ID payload
            yield f"data: {json.dumps({'type': 'init', 'thread_id': thread.id})}\n\n"

            async for event_item in stream_agent_query(
                message=body.message,
                thread_id=thread.id,
                memory_context=memory_context,
                document_context=document_context,
                user_id=current_user.id,
                image_path=stream_image_path,
            ):
                if isinstance(event_item, dict):
                    if event_item.get("type") == "token":
                        accumulated_text += event_item.get("content", "")
                    yield f"data: {json.dumps(event_item)}\n\n"
                elif isinstance(event_item, str):
                    accumulated_text += event_item
                    yield f"data: {json.dumps({'type': 'token', 'content': event_item})}\n\n"

            # Save assistant response to DB
            if accumulated_text:
                MessageRepository.add_message(
                    db,
                    thread_id=thread.id,
                    role="assistant",
                    content=accumulated_text
                )

            # Trigger background tasks
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

            updated_thread = ThreadRepository.get_thread(db, thread_id=thread.id, user_id=current_user.id)
            final_title = updated_thread.title if updated_thread else thread.title

            yield f"data: {json.dumps({'type': 'done', 'thread_id': thread.id, 'title': final_title, 'message': accumulated_text})}\n\n"

        except Exception as e:
            logger.error(f"Streaming failed: {repr(e)}", exc_info=True)
            err_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            yield f"data: {json.dumps({'type': 'error', 'error': err_msg})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
