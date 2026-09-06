from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.repositories import MemoryRepository
from app.schemas.chat import MemoryResponse

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("", response_model=List[MemoryResponse])
def get_user_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memories = MemoryRepository.get_user_memories(db, user_id=current_user.id)
    return memories


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    deleted = MemoryRepository.delete_memory(db, memory_id=memory_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found or access denied"
        )
    return None
