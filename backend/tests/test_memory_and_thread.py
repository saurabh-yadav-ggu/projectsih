import sys
import os
import asyncio
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal, init_db
from app.models.user import User
from app.repositories import CodingRepository, MemoryRepository
from app.memory import extract_and_save_memories, format_memories_for_prompt
from app.services.coding_runner import run_coding_agent_stream

async def run_tests():
    init_db()
    print("=" * 60)
    print("1. Testing Chatbot Long-Term Memory")
    print("=" * 60)
    
    test_user_id = 9999
    # Ensure test user in DB
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == test_user_id).first()
        if not user:
            user = User(
                id=test_user_id,
                name="Test Developer",
                email="test_thread@shield.ai",
                organisation="Shield",
                designation="AI Engineer",
                password="hashed_pw_test"
            )
            db.add(user)
            db.commit()

    # Test extracting long-term memory
    user_msg = "Hello! My name is Alex, I am a senior backend developer and my preferred database is PostgreSQL."
    print(f"Extracting memories from: '{user_msg}'")
    extract_and_save_memories(user_id=test_user_id, user_message=user_msg)

    # Check memories saved in DB
    with SessionLocal() as db:
        memories = MemoryRepository.get_user_memories(db, test_user_id)
        print(f"Retrieved {len(memories)} memories from DB:")
        for m in memories:
            print(f"  - [{m.memory_key}]: {m.memory_value}")
        
        prompt_block = format_memories_for_prompt(db, test_user_id)
        print("\nFormatted prompt block for chatbot context:\n" + prompt_block)
        assert len(memories) > 0, "Expected at least one memory to be extracted and saved!"

    print("\n" + "=" * 60)
    print("2. Testing Coding Assistant Conversation Thread Persistence")
    print("=" * 60)

    import uuid
    test_session_id = f"test-session-thread-{uuid.uuid4().hex[:8]}"
    
    # Save user message
    with SessionLocal() as db:
        msg1 = CodingRepository.save_message(
            db=db,
            session_id=test_session_id,
            user_id=test_user_id,
            role="user",
            content="Create a microservice in FastAPI for user authentication"
        )
        print(f"Saved user message ID={msg1.id}, thread_id={msg1.thread_id}")

        msg2 = CodingRepository.save_message(
            db=db,
            session_id=test_session_id,
            user_id=test_user_id,
            role="assistant",
            content="I will scaffold a FastAPI app with JWT authentication in /workspace/fastapi_auth."
        )
        print(f"Saved assistant message ID={msg2.id}, thread_id={msg2.thread_id}")

    # Retrieve messages from database
    with SessionLocal() as db:
        history = CodingRepository.get_messages(db, test_session_id, test_user_id)
        print(f"\nRetrieved {len(history)} messages from DB for session {test_session_id}:")
        for m in history:
            print(f"  [{m['role'].upper()}]: {m['content']}")
        assert len(history) == 2, f"Expected 2 messages in session history, got {len(history)}"

    print("\n" + "=" * 60)
    print("3. Testing Thread Execution & Model Context Retrieval")
    print("=" * 60)

    # Test run_coding_agent_stream with existing thread
    followup_prompt = "What was the previous instruction we discussed?"
    print(f"Sending follow-up prompt to coding agent: '{followup_prompt}'")
    
    received_chunks = []
    async for event in run_coding_agent_stream(
        session_id=test_session_id,
        user_id=test_user_id,
        user_prompt=followup_prompt,
        hitl_mode="open",
    ):
        event_type = event.get("type")
        if event_type == "agent_chunk":
            received_chunks.append(event.get("content", ""))
        elif event_type in ("agent_status", "agent_completed", "error"):
            print(f"Event: {event_type} - {event.get('status', '') or event.get('message', '')}")

    agent_output = "".join(received_chunks)
    print("\nAgent Response:")
    print(agent_output[:500] + ("..." if len(agent_output) > 500 else ""))

    # Verify that the new user prompt and assistant response were persisted to DB!
    with SessionLocal() as db:
        final_history = CodingRepository.get_messages(db, test_session_id, test_user_id)
        print(f"\nTotal conversation messages persisted in DB: {len(final_history)}")
        for idx, m in enumerate(final_history, 1):
            print(f"  {idx}. [{m['role'].upper()}]: {m['content'][:80]}...")
        assert len(final_history) >= 4, f"Expected at least 4 messages (2 prior + user prompt + assistant response), got {len(final_history)}"

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())
