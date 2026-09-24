from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.repositories import MemoryRepository


class StoreBackend:
    """
    StoreBackend for long-term persistent information:
    - User memories and personal preferences
    - Project context and metadata
    - Adapts to the existing SQLAlchemy long_term_memories table.
    """

    def __init__(self, db_session_factory=SessionLocal):
        self.session_factory = db_session_factory

    def get_user_memories(self, user_id: int) -> List[Dict[str, Any]]:
        db: Session = self.session_factory()
        try:
            mems = MemoryRepository.get_user_memories(db, user_id=user_id)
            return [
                {
                    "id": m.id,
                    "key": m.memory_key,
                    "value": m.memory_value,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                }
                for m in mems
            ]
        finally:
            db.close()

    def set_user_memory(self, user_id: int, key: str, value: str) -> Dict[str, Any]:
        db: Session = self.session_factory()
        try:
            mem = MemoryRepository.save_or_update_memory(db, user_id=user_id, key=key, value=value)
            return {
                "id": mem.id,
                "key": mem.memory_key,
                "value": mem.memory_value,
            }
        finally:
            db.close()

    def delete_user_memory(self, user_id: int, memory_id: int) -> bool:
        db: Session = self.session_factory()
        try:
            return MemoryRepository.delete_memory(db, memory_id=memory_id, user_id=user_id)
        finally:
            db.close()
