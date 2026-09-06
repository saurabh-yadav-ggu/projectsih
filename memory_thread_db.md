Modify my existing AI agent project to add a complete persistent conversation/thread system and long-term memory system using SQLite and SQLAlchemy.

IMPORTANT:

* Do NOT rewrite the existing RAG architecture.
* Continue using ChromaDB for RAG.
* Continue using Ollama for the LLM and embeddings.
* Continue using LangGraph/LangChain for the ReAct agent.
* Continue using MCP tools.
* Continue using the existing Vision tool.
* SQLite + SQLAlchemy should be used specifically for application-level users, conversations/threads, messages, titles, and long-term memories.
* The implementation must be clean, modular, and production-oriented.
* Do not use PostgreSQL for conversation memory.
* Do not store RAG vectors in SQLite.
* Do not duplicate the same conversation data unnecessarily.

============================================================

1. CURRENT ARCHITECTURE
   ============================================================

The existing project contains approximately:

app/
├── agent.py
├── rag.py
├── tools.py
├── vision.py
├── mcp.py
└── main.py

The current system has:

* Ollama LLM
* LangGraph ReAct agent
* ChromaDB RAG
* Ollama embeddings
* PDF ingestion using pypdf/PyPDFLoader
* Vision model through Ollama
* MCP tools
* FastAPI backend

Keep all of these existing capabilities working.

Add a proper persistence layer for:

1. Users
2. Threads/conversations
3. Messages
4. Conversation titles
5. Long-term memories

============================================================
2. DATABASE
===========

Use SQLite with SQLAlchemy 2.x.

Database:

sqlite:///./data/app.db

Create the database directory automatically if it does not exist.

Use SQLAlchemy ORM models.

Do not use raw SQL for normal CRUD operations.

Create a dedicated database module.

Recommended structure:

app/
├── agent.py
├── rag.py
├── tools.py
├── vision.py
├── mcp.py
├── database.py
├── models.py
├── repositories.py
├── memory.py
├── schemas.py
├── main.py
└── prompts/
└── prompt.json

============================================================
3. SQLALCHEMY MODELS
====================

Create the following models.

---

## User

Fields:

* id
* name
* email
* created_at
* updated_at

Use a UUID/string identifier if the existing authentication system already uses one.

If the existing authentication system already has a User model, reuse it instead of creating a duplicate User table.

---

## Thread / Conversation

Create a Conversation or Thread model.

Fields:

* id
* user_id
* title
* created_at
* updated_at

Requirements:

* Every conversation must have a unique thread_id.
* A thread belongs to exactly one user.
* A user can have multiple threads.
* Threads must be isolated between users.
* Default title should initially be something like "New conversation".
* Update the conversation's updated_at whenever a new message is added.

Example:

User 1:
thread_abc
thread_xyz

User 2:
thread_def

User 1 must never be able to access thread_def.

---

## Message

Create a Message model.

Fields:

* id
* thread_id
* role
* content
* created_at
* message_type

Possible roles:

* user
* assistant
* system
* tool

message_type can optionally represent:

* text
* tool_call
* tool_result
* image
* etc.

Store the actual conversation history in the Message table.

Do not depend exclusively on LangGraph checkpoint data for displaying conversation history.

The database should contain the application-level chat history.

---

## LongTermMemory

Create a LongTermMemory model.

Fields:

* id
* user_id
* memory_key
* memory_value
* created_at
* updated_at

Example:

user_id: user_123
memory_key: preferred_language
memory_value: Hindi

user_id: user_123
memory_key: preferred_framework
memory_value: FastAPI

user_id: user_123
memory_key: preferred_response_style
memory_value: concise

Long-term memories belong to the USER, not to a thread.

Therefore they must remain available across multiple conversations.

============================================================
4. DATABASE RELATIONSHIPS
=========================

Implement these relationships:

User
|
├── Conversations
│      |
│      └── Messages
│
└── LongTermMemories

Relationship:

User 1 ---- N Conversation

Conversation 1 ---- N Message

User 1 ---- N LongTermMemory

Use SQLAlchemy relationships where appropriate.

Add foreign keys and cascading behavior where appropriate.

============================================================
5. THREAD CREATION
==================

When the user starts a new conversation:

1. Generate a unique thread_id.
2. Create a Conversation record.
3. Associate it with the authenticated user.
4. Set an initial title.
5. Return the thread_id to the frontend.

Example response:

{
"thread_id": "8d7e9c3a-...",
"title": "New conversation"
}

Use UUIDs for thread IDs.

Do not use predictable integer IDs as public thread identifiers.

============================================================
6. THREAD CONTINUATION
======================

When the frontend sends:

thread_id = "abc..."

the backend must:

1. Authenticate the user.
2. Verify that the thread belongs to that user.
3. Load the conversation history.
4. Load relevant long-term memories.
5. Pass the required context to the LangGraph agent.
6. Run the agent.
7. Save the new user message.
8. Save the assistant response.
9. Update the conversation updated_at.

If the thread does not exist:

Return an appropriate 404 error.

If the thread belongs to another user:

Return 403 or 404 without exposing whether the thread exists.

============================================================
7. LANGGRAPH THREAD CONFIGURATION
=================================

Use the thread_id as the LangGraph thread identifier.

The LangGraph invocation should use:

config = {
"configurable": {
"thread_id": thread_id
}
}

The same thread_id must always map to the same conversation.

Do not generate a new thread_id for every message.

The thread_id should remain stable for the lifetime of the conversation.

============================================================
8. LANGGRAPH CHECKPOINTING
==========================

Do not assume that the LangGraph checkpointer alone is the application's chat-history database.

Use LangGraph checkpointing for agent execution/state persistence when appropriate.

Use SQLAlchemy SQLite tables for application-level:

* conversations
* titles
* messages
* long-term memories

The frontend's conversation history should come from the Message table.

This separation is important:

LangGraph checkpoint:
Agent execution state

SQLAlchemy Message:
Application chat history

SQLAlchemy Conversation:
Thread metadata

SQLAlchemy LongTermMemory:
Persistent user memory

ChromaDB:
RAG documents and embeddings

============================================================
9. CONVERSATION HISTORY
=======================

Every user message must be persisted.

Every final assistant response must be persisted.

Example:

User:
"Explain FastAPI."

Database:

thread_id = abc

message 1:
role = user
content = "Explain FastAPI."

message 2:
role = assistant
content = "FastAPI is..."

When a new message arrives, append it rather than replacing previous messages.

The API should provide an endpoint to retrieve conversation history.

Example:

GET /api/threads/{thread_id}/messages

Response:

{
"thread_id": "abc",
"messages": [
{
"id": "...",
"role": "user",
"content": "Hello",
"created_at": "..."
},
{
"id": "...",
"role": "assistant",
"content": "Hello! How can I help?",
"created_at": "..."
}
]
}

============================================================
10. CONVERSATION TITLE
======================

Implement automatic conversation title generation.

When a new conversation starts, initially use:

"New conversation"

After the first meaningful user message, generate a short title.

Example:

User:
"How do I implement JWT authentication in FastAPI?"

Title:

"FastAPI JWT Authentication"

Another example:

User:
"Explain vector databases and RAG."

Title:

"Vector Databases and RAG"

Requirements:

* Maximum approximately 50-80 characters.
* No unnecessary punctuation.
* Do not generate a long sentence.
* Title should describe the conversation topic.
* Generate title using the existing Ollama LLM.
* Do not call the title-generation model on every message.
* Generate/update the title only when appropriate.

Prefer generating the title after the first user message.

If title generation fails, keep:

"New conversation"

Do not fail the entire chat request because title generation failed.

============================================================
11. TITLE GENERATION PROMPT
===========================

Create a separate title prompt.

Example:

"You are a conversation title generator.

Generate a short, descriptive title for the following user message.

Rules:

* Maximum 60 characters.
* No quotes.
* No markdown.
* Do not explain anything.
* Return only the title.

User message:
{message}"

Load prompts from the existing prompt.json architecture instead of hardcoding large prompts inside agent.py.

============================================================
12. LONG-TERM MEMORY
====================

Implement persistent long-term memory.

Long-term memory is different from conversation history.

Conversation history:

"What happened in this conversation?"

Long-term memory:

"What useful information should the assistant remember about this user across conversations?"

Examples of long-term memories:

* User prefers Python.
* User prefers concise answers.
* User works with FastAPI.
* User is building an AI agent.
* User prefers code examples.
* User prefers ChromaDB.
* User prefers Ollama for local models.

Do NOT store every message as long-term memory.

Only store durable, useful information.

============================================================
13. MEMORY EXTRACTION
=====================

Implement automatic memory extraction.

After a user message, determine whether it contains useful long-term information.

For example:

"My preferred programming language is Python."

Should produce:

{
"memory_key": "preferred_programming_language",
"memory_value": "Python"
}

Another:

"I prefer concise answers."

Should produce:

{
"memory_key": "response_preference",
"memory_value": "concise"
}

But:

"What is Python?"

Should NOT create a long-term memory.

Likewise:

"Calculate 20 * 30"

should NOT create memory.

Do not store temporary conversation details as long-term memory.

============================================================
14. MEMORY EXTRACTION LLM
=========================

Use the existing Ollama model to extract memories.

The extraction result must be structured.

Prefer Pydantic structured output.

Example schema:

class MemoryItem(BaseModel):
key: str
value: str

class MemoryExtraction(BaseModel):
memories: list[MemoryItem]

If no useful memory exists:

{
"memories": []
}

The memory extraction step must never break the main chat if it fails.

If memory extraction fails:

* Log the error.
* Continue the conversation normally.

============================================================
15. MEMORY DEDUPLICATION
========================

Do not create duplicate memories.

If the user already has:

preferred_language = Python

and later says:

"I prefer Python."

do not create another identical record.

If the user changes the information:

"I now prefer TypeScript."

update the existing relevant memory instead of creating unnecessary duplicates.

Use:

user_id + memory_key

as a logical uniqueness constraint.

============================================================
16. MEMORY RETRIEVAL
====================

Before running the main agent:

1. Identify the authenticated user.
2. Retrieve that user's long-term memories.
3. Convert relevant memories into context.
4. Provide the memory context to the agent.

Example:

User memories:

* preferred_language: Python
* preferred_framework: FastAPI
* response_preference: concise

Agent context:

User memory:

* Preferred programming language: Python
* Preferred framework: FastAPI
* Response preference: concise

Use memories to improve responses, but do not blindly treat every memory as authoritative if the user contradicts it.

============================================================
17. MEMORY PRIVACY / ISOLATION
==============================

This is extremely important.

Never retrieve long-term memory using only:

memory_key

Always filter by authenticated user_id.

Correct:

WHERE user_id = authenticated_user_id

Never allow the LLM to decide which user_id to access.

The user_id must come from the authenticated backend/session.

The LLM must never be trusted to enforce authorization.

============================================================
18. DO NOT EXPOSE INTERNAL MEMORY
=================================

Do not automatically show internal memory records to the user during normal chat.

Memory should silently improve the assistant's responses.

Optionally create a separate API:

GET /api/memory

to allow the authenticated user to view their stored memories.

Also provide:

DELETE /api/memory/{memory_id}

so the user can delete an unwanted memory.

============================================================
19. MEMORY MANAGEMENT API
=========================

Add endpoints such as:

POST /api/threads

Create a new thread.

GET /api/threads

List authenticated user's conversations.

GET /api/threads/{thread_id}

Get thread metadata.

GET /api/threads/{thread_id}/messages

Get conversation history.

DELETE /api/threads/{thread_id}

Delete a conversation.

GET /api/memory

List user's long-term memories.

DELETE /api/memory/{memory_id}

Delete a long-term memory.

============================================================
20. THREAD LIST
===============

GET /api/threads should return something like:

[
{
"thread_id": "abc",
"title": "FastAPI JWT Authentication",
"created_at": "...",
"updated_at": "..."
},
{
"thread_id": "xyz",
"title": "RAG with ChromaDB",
"created_at": "...",
"updated_at": "..."
}
]

Sort conversations by:

updated_at DESC

This allows the frontend to display a ChatGPT/Claude-style sidebar.

============================================================
21. DELETE THREAD
=================

When deleting a thread:

* Delete the conversation.
* Delete all messages belonging to that thread.
* Do NOT delete the user's long-term memories.

Deleting a conversation should not delete user-level memories.

For example:

Conversation:
"FastAPI project discussion"

can be deleted.

But:

User memory:
"User prefers Python"

must remain.

============================================================
22. FASTAPI INTEGRATION
=======================

Modify main.py to support thread-based chat.

Example endpoint:

POST /api/chat

Request:

{
"thread_id": "abc",
"message": "Explain RAG"
}

The backend should:

1. Authenticate user.
2. Validate thread ownership.
3. Save user message.
4. Retrieve long-term memory.
5. Run LangGraph agent using thread_id.
6. Save assistant response.
7. Update thread timestamp.
8. Return response.

Response:

{
"thread_id": "abc",
"message": {
"role": "assistant",
"content": "..."
}
}

============================================================
23. NEW CHAT FLOW
=================

Frontend:

POST /api/threads

Backend:

Create UUID.

Create database record.

Return:

{
"thread_id": "...",
"title": "New conversation"
}

Then frontend sends:

POST /api/chat

{
"thread_id": "...",
"message": "Hello"
}

============================================================
24. EXISTING CHAT FLOW
======================

Frontend sends:

POST /api/chat

{
"thread_id": "existing-thread-id",
"message": "Continue what we discussed earlier."
}

Backend:

Authenticate user
↓
Validate thread ownership
↓
Load long-term memory
↓
Load conversation state
↓
Run LangGraph
↓
Save message
↓
Return response

============================================================
25. AGENT CONTEXT
=================

The agent should receive:

1. System prompt
2. Relevant conversation history/state
3. Relevant long-term memory
4. Current user message

Do not blindly inject thousands of old messages into every LLM call.

Use LangGraph checkpoint/thread state and appropriate message trimming/summarization when conversation history becomes large.

Keep the system scalable.

============================================================
26. MESSAGE DUPLICATION
=======================

Avoid saving the same assistant response multiple times.

If LangGraph returns multiple AI/tool messages, identify the final user-facing assistant response before saving it as the assistant chat message.

Tool calls/tool results may optionally be stored separately for debugging, but the normal conversation history should primarily contain user and final assistant messages.

============================================================
27. DATABASE SESSION MANAGEMENT
===============================

Create a proper SQLAlchemy session dependency.

Example concept:

def get_db():
with SessionLocal() as session:
yield session

Use dependency injection in FastAPI.

Do not create a new database engine for every query.

Create one SQLAlchemy engine and session factory.

Use:

create_engine(...)

sessionmaker / async_sessionmaker as appropriate.

Prefer SQLAlchemy 2.x patterns.

============================================================
28. DATABASE INITIALIZATION
===========================

On application startup:

1. Ensure ./data exists.
2. Create database tables if they do not exist.
3. Initialize the application database.

For a small application, SQLAlchemy metadata creation is acceptable.

Keep the architecture ready for Alembic migrations later.

============================================================
29. ENVIRONMENT VARIABLES
=========================

Move configuration into environment variables.

Example:

DATABASE_URL=sqlite:///./data/app.db

OLLAMA_BASE_URL=http://localhost:11434

OLLAMA_MODEL=qwen3:8b

VISION_MODEL=qwen3-vl:4b-instruct

EMBEDDING_MODEL=qwen3-embedding:0.6b

CHROMA_PERSIST_DIRECTORY=./chroma_db

Do not hardcode secrets.

============================================================
30. EXISTING PROMPT.JSON
========================

The existing system prompt is stored in:

prompt.json

Continue loading it from JSON.

Do not duplicate the entire system prompt inside agent.py.

Add additional prompts such as:

* system_prompt
* title_generation_prompt
* memory_extraction_prompt

Example structure:

{
"system_prompt": "...",
"title_generation_prompt": "...",
"memory_extraction_prompt": "..."
}

Load the JSON safely with pathlib and json.

If a required prompt is missing, raise a clear configuration error.

============================================================
31. LONG-TERM MEMORY PROMPT
===========================

Use a strict prompt similar to:

"You are a memory extraction system.

Analyze the user's message and identify only durable information that could improve future conversations.

Store information such as:

* stable preferences
* programming preferences
* communication preferences
* recurring project information
* useful user preferences

Do NOT store:

* temporary requests
* one-time calculations
* ordinary questions
* sensitive information unless explicitly required and permitted
* secrets
* passwords
* API keys
* authentication tokens

Return structured output.

If there is no useful long-term memory, return an empty list."

============================================================
32. MEMORY EXECUTION STRATEGY
=============================

Do not make long-term memory extraction block the user's main response unnecessarily.

Prefer:

User message
↓
Main agent response
↓
Memory extraction
↓
Save useful memories

If implemented asynchronously/background:

* Memory extraction failure must not affect the chat response.
* Database failures must be logged.
* Do not lose the main assistant response because memory storage failed.

For the initial implementation, a sequential implementation is acceptable if it keeps the code simpler and reliable.

============================================================
33. RAG SEPARATION
==================

Do not mix long-term memory with RAG documents.

ChromaDB:

* PDFs
* documents
* manuals
* knowledge base
* embeddings

SQLite:

* users
* threads
* messages
* titles
* long-term memories

These are separate concerns.

Do not embed every chat message into ChromaDB unless explicitly required.

============================================================
34. FILE STRUCTURE
==================

Implement the final structure approximately as:

project/
│
├── app/
│   ├── **init**.py
│   │
│   ├── agent.py
│   ├── rag.py
│   ├── tools.py
│   ├── vision.py
│   ├── mcp.py
│   │
│   ├── database.py
│   ├── models.py
│   ├── repositories.py
│   ├── memory.py
│   ├── schemas.py
│   │
│   ├── config.py
│   └── main.py
│
├── prompts/
│   └── prompt.json
│
├── data/
│   └── app.db
│
├── chroma_db/
│
├── documents/
│
├── .env
├── requirements.txt
└── README.md

Adapt the structure to the existing project rather than unnecessarily moving existing files.

============================================================
35. CODE QUALITY
================

Use:

* Type hints
* SQLAlchemy 2.x
* Pydantic models for API schemas
* Proper exception handling
* Dependency injection
* UUID thread IDs
* Repository/service separation where useful
* Clear function names
* Small reusable functions
* Environment-based configuration
* Logging

Do not put all database logic inside main.py.

Do not put all memory logic inside agent.py.

Do not put authentication logic inside the LLM.

============================================================
36. ERROR HANDLING
==================

Handle:

* Invalid thread ID
* Thread not found
* Unauthorized thread access
* Database connection errors
* LLM errors
* MCP errors
* RAG errors
* Memory extraction errors
* Title generation errors

A failure in title generation or long-term memory extraction must not cause the main chat response to fail.

============================================================
37. TESTING
===========

Add basic tests for:

1. Create thread.
2. Create two threads for same user.
3. Verify threads are isolated.
4. Save user message.
5. Save assistant message.
6. Retrieve conversation history.
7. Generate/update title.
8. Save long-term memory.
9. Retrieve long-term memory.
10. Update existing memory.
11. Delete memory.
12. Delete thread.
13. Verify deleting a thread does not delete long-term memory.
14. Verify one user cannot access another user's thread.
15. Verify one user cannot access another user's memory.

============================================================
38. IMPORTANT SECURITY REQUIREMENTS
===================================

Never trust:

* thread_id from the frontend
* user_id from the frontend
* memory ownership from the frontend

Always derive authenticated user identity from the backend authentication system.

Every thread query must include the authenticated user ID.

Every memory query must include the authenticated user ID.

Example:

WHERE conversation.id = thread_id
AND conversation.user_id = authenticated_user_id

Never:

WHERE conversation.id = thread_id

by itself.

============================================================
39. FINAL AGENT FLOW
====================

The complete request flow should be:

User
↓
FastAPI
↓
Authentication
↓
user_id
↓
thread_id validation
↓
SQLite / SQLAlchemy
├── Load conversation
├── Load message history if needed
└── Load long-term memory
↓
LangGraph ReAct Agent
├── Ollama
├── RAG → ChromaDB
├── Vision → Ollama Vision
└── MCP → MCP Server
↓
Final assistant response
↓
SQLite / SQLAlchemy
├── Save user message
├── Save assistant message
├── Update thread
└── Save extracted long-term memory
↓
FastAPI response
↓
Frontend

============================================================
40. DO NOT BREAK EXISTING FEATURES
==================================

After implementation verify that:

* Existing RAG works.
* PDF ingestion using pypdf works.
* ChromaDB search works.
* Vision works.
* MCP tools work.
* Ollama works.
* ReAct tool calling works.
* Existing prompt.json loading works.
* Existing FastAPI endpoints continue working where applicable.

Do not remove existing functionality merely to implement memory.

============================================================
41. DELIVERABLE
===============

Provide the complete modified code for all affected files.

For every modified file:

* Show the complete file.
* Do not show partial snippets.
* Clearly explain what changed.
* Include required imports.
* Include database models.
* Include SQLAlchemy setup.
* Include Pydantic schemas.
* Include thread APIs.
* Include message persistence.
* Include title generation.
* Include long-term memory extraction.
* Include memory retrieval.
* Include thread ownership validation.
* Include environment configuration.

Also update requirements.txt with the required packages.

Finally provide exact commands to:

1. Install dependencies.
2. Start SQLite/database setup.
3. Start Ollama.
4. Start the FastAPI server.
5. Create a new thread.
6. Send a message.
7. Retrieve conversation history.
8. List threads.
9. Retrieve long-term memories.

Do not leave TODOs or placeholder functions.

The final implementation should be runnable rather than pseudocode.


============================================================
42. IMPLEMENTATION COMPLETED & STATUS UPDATE
============================================================

### Implementation Summary
The persistent conversation/thread management and long-term memory system has been fully implemented using **SQLite + SQLAlchemy 2.x** without altering the existing RAG (ChromaDB), Ollama LLM/Embeddings, Vision tool, or MCP integration.

### Implemented File Structure & Modules

```
backend/
├── pyproject.toml        # Installed dependencies & package discovery rules
├── requirements.txt      # Fixed dependencies (including langchain-mcp-adapters)
└── app/
    ├── config.py         # Pydantic settings loading environment variables
    ├── database.py       # SQLite connection engine & init_db() startup hook
    ├── prompt.json       # System prompt, Title prompt & Memory extraction prompt
    ├── repositories.py   # ThreadRepository, MessageRepository & MemoryRepository
    ├── memory.py         # Automated Memory extraction & Title generation
    ├── agent.py          # LangGraph ReAct agent with checkpointer & prompt memory injection
    ├── rag.py            # ChromaDB vector store retriever & document loaders
    ├── vision.py         # Ollama Vision analysis
    ├── models/
    │   ├── user.py       # User ORM model
    │   └── chat.py       # Conversation, Message & LongTermMemory ORM models
    ├── schemas/
    │   ├── auth.py       # Authentication request/response schemas
    │   └── chat.py       # Thread, Message & Memory request/response schemas
    ├── mcp/
    │   └── mcp_client.py # Safe MCP tool loader with fallback
    └── routers/
        ├── auth.py       # Authentication routes (/auth/register, /auth/login, /auth/me)
        ├── threads.py    # Thread management routes (/api/threads)
        ├── memory.py     # Memory management routes (/api/memory)
        ├── chat.py       # Agent execution endpoint (/api/chat)
        └── upload.py     # Document ingestion route (/api/upload)
```

### Verified Features & Security Enforcements

1. **User-Scoped Thread Isolation**:
   All database queries for retrieving, viewing, or deleting threads and messages enforce `WHERE thread_id = :id AND user_id = :authenticated_user_id`.

2. **User-Scoped Long-Term Memory**:
   Long-term memories are attached directly to the user (not to an individual thread) and deduplicated via `(user_id, memory_key)` constraints. They are dynamically formatted and injected into the agent system prompt context.

3. **Automatic Non-Blocking Title Generation & Memory Extraction**:
   When a user sends a message, title generation (for new threads) and long-term memory extraction run as background tasks so they do not block or delay the main chat response.

4. **Separation of Concerns**:
   - **ChromaDB**: Dedicated to RAG document chunks & embeddings.
   - **SQLite (`data/app.db`)**: Stores users, threads, application chat history, and long-term memories.
   - **SQLite Checkpointer (`data/checkpoints.db`)**: Manages persistent agent execution state using `SqliteSaver`.

---

### Commands to Run & Test

```powershell
# 1. Install dependencies
cd d:\sih\project\backend
uv sync

# 2. Run Database Initializer & Start FastAPI Backend
uv run uvicorn app.main:app --reload --port 8000
```

