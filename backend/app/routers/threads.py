from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.repositories import ThreadRepository, MessageRepository
from app.schemas.chat import ThreadCreate, ThreadResponse, MessageResponse

router = APIRouter(prefix="/api/threads", tags=["threads"])


@router.post("", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_thread(
    body: ThreadCreate = ThreadCreate(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    thread = ThreadRepository.create_thread(
        db,
        user_id=current_user.id,
        title=body.title or "New conversation"
    )
    return thread


@router.get("", response_model=List[ThreadResponse])
def list_threads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ThreadRepository.list_threads(db, user_id=current_user.id)


@router.get("/{thread_id}", response_model=ThreadResponse)
def get_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    thread = ThreadRepository.get_thread(db, thread_id=thread_id, user_id=current_user.id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found or access denied"
        )
    return thread


@router.get("/{thread_id}/messages", response_model=List[MessageResponse])
def get_thread_messages(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    thread = ThreadRepository.get_thread(db, thread_id=thread_id, user_id=current_user.id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found or access denied"
        )
    messages = MessageRepository.get_messages(db, thread_id=thread_id, user_id=current_user.id)
    return messages


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = ThreadRepository.delete_thread(db, thread_id=thread_id, user_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found or access denied"
        )
    return None
