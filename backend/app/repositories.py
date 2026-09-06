from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.chat import Conversation, Message, LongTermMemory


class ThreadRepository:
    @staticmethod
    def create_thread(db: Session, user_id: int, title: str = "New conversation") -> Conversation:
        thread = Conversation(
            user_id=user_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)
        return thread

    @staticmethod
    def get_thread(db: Session, thread_id: str, user_id: int) -> Optional[Conversation]:
        """Strict ownership check: thread must belong to user_id."""
        return (
            db.query(Conversation)
            .filter(Conversation.id == thread_id, Conversation.user_id == user_id)
            .first()
        )

    @staticmethod
    def list_threads(db: Session, user_id: int) -> List[Conversation]:
        """List user threads sorted by updated_at descending."""
        return (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    @staticmethod
    def delete_thread(db: Session, thread_id: str, user_id: int) -> bool:
        thread = ThreadRepository.get_thread(db, thread_id, user_id)
        if not thread:
            return False
        db.delete(thread)
        db.commit()
        return True

    @staticmethod
    def update_title(db: Session, thread_id: str, user_id: int, title: str) -> Optional[Conversation]:
        thread = ThreadRepository.get_thread(db, thread_id, user_id)
        if thread:
            thread.title = title
            thread.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(thread)
        return thread

    @staticmethod
    def touch_thread(db: Session, thread_id: str, user_id: int):
        thread = ThreadRepository.get_thread(db, thread_id, user_id)
        if thread:
            thread.updated_at = datetime.utcnow()
            db.commit()


class MessageRepository:
    @staticmethod
    def add_message(db: Session, thread_id: str, role: str, content: str, message_type: str = "text") -> Message:
        msg = Message(
            thread_id=thread_id,
            role=role,
            content=content,
            message_type=message_type,
            created_at=datetime.utcnow()
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def get_messages(db: Session, thread_id: str, user_id: int) -> List[Message]:
        thread = ThreadRepository.get_thread(db, thread_id, user_id)
        if not thread:
            return []
        return (
            db.query(Message)
            .filter(Message.thread_id == thread_id)
            .order_by(Message.created_at.asc())
            .all()
        )


class MemoryRepository:
    @staticmethod
    def get_user_memories(db: Session, user_id: int) -> List[LongTermMemory]:
        """Fetch all long-term memories for a user."""
        return (
            db.query(LongTermMemory)
            .filter(LongTermMemory.user_id == user_id)
            .order_by(LongTermMemory.created_at.desc())
            .all()
        )

    @staticmethod
    def save_or_update_memory(db: Session, user_id: int, memory_key: str, memory_value: str) -> LongTermMemory:
        """Update existing memory if key exists for user; otherwise insert."""
        key = memory_key.strip().lower().replace(" ", "_")
        existing = (
            db.query(LongTermMemory)
            .filter(LongTermMemory.user_id == user_id, LongTermMemory.memory_key == key)
            .first()
        )
        if existing:
            existing.memory_value = memory_value
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing

        new_mem = LongTermMemory(
            user_id=user_id,
            memory_key=key,
            memory_value=memory_value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_mem)
        db.commit()
        db.refresh(new_mem)
        return new_mem

    @staticmethod
    def delete_memory(db: Session, memory_id: str, user_id: int) -> bool:
        mem = (
            db.query(LongTermMemory)
            .filter(LongTermMemory.id == memory_id, LongTermMemory.user_id == user_id)
            .first()
        )
        if not mem:
            return False
        db.delete(mem)
        db.commit()
        return True
