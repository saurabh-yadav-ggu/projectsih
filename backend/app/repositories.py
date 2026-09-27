from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from pathlib import Path
from app.models.chat import Conversation, Message, LongTermMemory
from app.models.coding import CodingSession, CodingApproval


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


class CodingRepository:
    @staticmethod
    def create_session(
        db: Session,
        user_id: int,
        workspace_path: str,
        title: str = "Coding Session",
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> CodingSession:
        kwargs = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "title": title,
            "workspace_path": workspace_path,
            "model": model,
            "status": "idle",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        if session_id:
            kwargs["id"] = session_id
        session = CodingSession(**kwargs)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_session(db: Session, session_id: str, user_id: int) -> Optional[CodingSession]:
        return (
            db.query(CodingSession)
            .filter(CodingSession.id == session_id, CodingSession.user_id == user_id)
            .first()
        )

    @staticmethod
    def list_sessions(db: Session, user_id: int) -> List[CodingSession]:
        return (
            db.query(CodingSession)
            .filter(CodingSession.user_id == user_id)
            .order_by(CodingSession.updated_at.desc())
            .all()
        )

    @staticmethod
    def update_session_status(db: Session, session_id: str, user_id: int, status: str) -> Optional[CodingSession]:
        session = CodingRepository.get_session(db, session_id, user_id)
        if session:
            session.status = status
            session.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(session)
        return session

    @staticmethod
    def update_session_workspace(db: Session, session_id: str, user_id: int, workspace_path: str) -> Optional[CodingSession]:
        session = CodingRepository.get_session(db, session_id, user_id)
        if session:
            session.workspace_path = workspace_path
            session.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(session)
            return session
        else:
            return CodingRepository.create_session(
                db=db,
                user_id=user_id,
                workspace_path=workspace_path,
                session_id=session_id,
                title=f"Session: {Path(workspace_path).name}",
            )

    @staticmethod
    def delete_session(db: Session, session_id: str, user_id: int) -> bool:
        session = CodingRepository.get_session(db, session_id, user_id)
        if not session:
            return False
        db.delete(session)
        db.commit()
        return True

    @staticmethod
    def record_approval(
        db: Session,
        session_id: str,
        request_id: str,
        action: str,
        command: str,
        risk_level: str = "medium"
    ) -> CodingApproval:
        approval = CodingApproval(
            session_id=session_id,
            request_id=request_id,
            action=action,
            command=command,
            risk_level=risk_level,
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        return approval

    create_approval = record_approval

    @staticmethod
    def resolve_approval(db: Session, session_id: str, request_id: str, status: str) -> Optional[CodingApproval]:
        approval = (
            db.query(CodingApproval)
            .filter(CodingApproval.session_id == session_id, CodingApproval.request_id == request_id)
            .first()
        )
        if approval:
            approval.status = status
            db.commit()
            db.refresh(approval)
        return approval

    @staticmethod
    def ensure_session_conversation(db: Session, session_id: str, user_id: int) -> Conversation:
        session = CodingRepository.get_session(db, session_id, user_id)
        if not session:
            session = CodingRepository.create_session(
                db=db,
                user_id=user_id,
                workspace_path="",
                session_id=session_id,
                title="Coding Session"
            )

        if session.conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == session.conversation_id).first()
            if conv:
                return conv

        conv_title = session.title or "Coding Session"
        conv = Conversation(
            user_id=user_id,
            title=conv_title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        session.conversation_id = conv.id
        db.commit()
        db.refresh(session)
        return conv

    @staticmethod
    def save_message(db: Session, session_id: str, user_id: int, role: str, content: str) -> Message:
        conv = CodingRepository.ensure_session_conversation(db, session_id, user_id)
        msg = Message(
            thread_id=conv.id,
            role=role,
            content=content,
            created_at=datetime.utcnow()
        )
        db.add(msg)
        conv.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def get_messages(db: Session, session_id: str, user_id: int) -> List[Dict[str, Any]]:
        session = CodingRepository.get_session(db, session_id, user_id)
        if not session or not session.conversation_id:
            return []
        msgs = (
            db.query(Message)
            .filter(Message.thread_id == session.conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.created_at.isoformat() if m.created_at else datetime.utcnow().isoformat(),
                "tools": []
            }
            for m in msgs
        ]

