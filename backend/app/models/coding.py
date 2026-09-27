import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base


class CodingSession(Base):
    __tablename__ = "coding_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String, nullable=False, default="Coding Session")
    workspace_path = Column(String, nullable=False)
    model = Column(String, nullable=True)
    status = Column(String, nullable=False, default="idle")  # idle, thinking, executing, waiting_approval, completed, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="coding_sessions")
    conversation = relationship("Conversation", back_populates="coding_sessions")
    approvals = relationship(
        "CodingApproval",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="CodingApproval.created_at.desc()"
    )


class CodingApproval(Base):
    __tablename__ = "coding_approvals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("coding_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # execute, write_file, edit_file
    command = Column(Text, nullable=False)
    risk_level = Column(String, default="medium")  # low, medium, high
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("CodingSession", back_populates="approvals")
