# Shield AI — Deep Agent Architecture Migration Plan

## 1. Current Architecture
- **Framework**: FastAPI (v0.141.1) + LangChain (v1.4.0) + LangGraph (v1.2.11) + React 19 / Vite.
- **Agent Architecture**: Monolithic ReAct Agent using `create_agent` in `backend/app/agent.py` with `AsyncSqliteSaver` checkpointer.
- **RAG & Storage**: ChromaDB vector store with Ollama `embeddinggemma`, SQLite with SQLAlchemy for threads, messages, and long-term memory.
- **Tools**: Handcrafted local tools in `backend/app/tools.py` mixed with `mcp-docgen` tools via `backend/app/mcp/mcp_client.py`.
- **Execution**: Direct Python execution in the host process for document writers; hardcoded tool schemas.

## 2. Target Architecture
- **Main Supervisor Deep Agent**: Orchestrator responsible for intent analysis, planning, capability routing, subagent delegation, result synthesis, and artifact verification loops.
- **Specialized Subagents**:
  - `ChatAgent`: Normal conversational interactions, reasoning, Q&A, and calculations.
  - `DocumentAgent`: Document generation coordinating skills, code generation, sandboxing, and verification.
  - `RAGAgent`: Document retrieval with user and thread scoping.
  - `VisionAgent`: Multimodal image and diagram understanding via local Ollama vision.
  - `CodingAgent`: Python code generation, execution in isolated sandbox, diagnostic repair loops.
  - `VerificationAgent`: Automated artifact validation across DOCX, XLSX, PPTX, PDF, and HTML.
- **Skill System**: Hierarchical markdown skill files (`backend/skills/`) loaded contextually on-demand.
- **Composite Backend**:
  - `StateBackend`: Thread execution and agent scratchpad state.
  - `StoreBackend`: Persistent user memory and thread metadata adapter.
  - `FilesystemBackend`: User-isolated workspace (`backend/workspace/users/{user_id}/`).
- **Sandbox Execution**: Subprocess isolation with AST security checks, strict resource limits, timeouts, and optional Docker support.
- **Dynamic MCP Tools**: Configurable MCP servers loading tools dynamically without hardcoding.
- **Streaming & UI**: SSE events for `plan`, `subagent_start`, `subagent_result`, `tool_start`, `tool_end`, `artifact_created`, `verification`, `token`, `done`, `error`.

## 3. Files to Reuse & Preserve
- `backend/app/models/*` (User, Conversation, Message, LongTermMemory)
- `backend/app/repositories.py` (ThreadRepository, MessageRepository, MemoryRepository)
- `backend/app/core/*` (Security, JWT tokens)
- `backend/app/routers/auth.py`, `backend/app/routers/threads.py`, `backend/app/routers/documents.py`, `backend/app/routers/upload.py`, `backend/app/routers/memory.py`
- `backend/app/config.py` & `backend/app/database.py`

## 4. Files to Refactor
- `backend/app/agent.py` -> Backward-compatible wrapper exposing `run_agent_query` and `stream_agent_query`, delegating to `backend/app/agent/main_agent.py`.
- `backend/app/rag.py` -> Modularized into `backend/app/rag/` with facade in `backend/app/rag.py`.
- `backend/app/mcp/mcp_client.py` -> Dynamic MCP configuration loader with Ollama newline sanitization.
- `backend/app/routers/chat.py` -> Emit rich SSE events (`subagent_start`, `artifact_created`, `verification`).
- `frontend/src/api/chat.js` & `frontend/src/components/chat/*` -> Handle pipeline events and render status pills.

## 5. Files to Create
- `backend/skills/*` (documents, docx, xlsx, pptx, pdf, csv, html, coding, rag, vision, chat, verification)
- `backend/app/backends/*` (state, store, filesystem, composite)
- `backend/app/sandbox/*` (models, security, executor, docker_executor)
- `backend/app/verification/*` (artifact, document, code)
- `backend/app/agent/*` (main_agent, state, prompts, planner, router, delegation)
- `backend/app/agent/subagents/*` (chat_agent, rag_agent, vision_agent, coding_agent, document_agent, verification_agent)
- `backend/app/rag/*` (ingestion, retrieval, embeddings)
- `backend/app/mcp/adapters.py`

## 6. Migration Sequence
1. Skills System Creation
2. Sandbox Execution Engine
3. Artifact & Document Verification Engine
4. Composite Backend & Filesystem Isolation
5. Dynamic MCP Client & Adapters
6. Modular RAG Refactor
7. Subagents Implementation
8. Main Deep Agent Supervisor Implementation
9. FastAPI Chat Router Streaming Update
10. Frontend React Streaming & Status UI Update
11. Unit & Regression Verification
