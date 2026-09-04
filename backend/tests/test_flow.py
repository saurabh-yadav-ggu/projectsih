import warnings
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.user import User
from app.core.security import create_access_token, SECRET_KEY
from app.repositories import ThreadRepository, MessageRepository, MemoryRepository
from app.memory import format_memories_for_prompt, _clean_json_response

engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_jwt_key_length_no_warning():
    """Verify that JWT token encoding/decoding triggers zero InsecureKeyLengthWarning warnings."""
    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        assert len(SECRET_KEY.encode("utf-8")) >= 32

        token = create_access_token({"sub": "test@example.com"})
        assert token is not None

        for w in recorded_warnings:
            assert "InsecureKeyLengthWarning" not in str(w.category)


def test_memory_cleaning_and_resilience():
    """Verify JSON cleaning and memory extraction parsing edge-cases."""
    raw_markdown = "```json\n[{\"key\": \"user_role\", \"value\": \"AI Research Engineer\"}]\n```"
    cleaned = _clean_json_response(raw_markdown)
    assert cleaned == '[{"key": "user_role", "value": "AI Research Engineer"}]'


def test_memory_repository_and_formatting():
    """Verify memory saving, updating, and formatting into system prompt context."""
    db = TestingSessionLocal()
    try:
        user = User(
            email="test@example.com",
            name="Test User",
            organisation="ShieldOrg",
            designation="AI Eng",
            password="hashed_pass"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        mem1 = MemoryRepository.save_or_update_memory(db, user.id, "user_role", "Backend Engineer")
        assert mem1.memory_key == "user_role"
        assert mem1.memory_value == "Backend Engineer"

        mem2 = MemoryRepository.save_or_update_memory(db, user.id, "user_role", "Senior AI Engineer")
        assert mem2.memory_value == "Senior AI Engineer"

        ctx = format_memories_for_prompt(db, user.id)
        assert "User Role: Senior AI Engineer" in ctx
    finally:
        db.close()


def test_thread_and_message_repository():
    """Verify thread creation, message additions, and query retrieval."""
    db = TestingSessionLocal()
    try:
        user = User(
            email="test2@example.com",
            name="Test User 2",
            organisation="ShieldOrg",
            designation="AI Eng",
            password="hashed_pass"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        thread = ThreadRepository.create_thread(db, user.id, title="Test Thread")
        assert thread.id is not None
        assert thread.title == "Test Thread"

        msg1 = MessageRepository.add_message(db, thread.id, role="user", content="Hello ShieldAI")
        msg2 = MessageRepository.add_message(db, thread.id, role="assistant", content="Hello! How can I assist you?")

        messages = MessageRepository.get_messages(db, thread.id, user.id)
        assert len(messages) == 2
        assert messages[0].content == "Hello ShieldAI"
        assert messages[1].content == "Hello! How can I assist you?"
    finally:
        db.close()
