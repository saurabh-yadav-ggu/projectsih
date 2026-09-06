# Shield AI - React Frontend & FastAPI Backend Integration Documentation

## 1. Overview & Architecture

This document describes the complete integration between the **React Frontend** (`http://localhost:5173`) and the **FastAPI Backend Service** (`http://localhost:8000`), implementing persistent conversation threads, message history, automated title generation, and long-term memory extraction.

---

## 2. API Endpoints Exposed by `main.py`

### **System & Health**
- `GET /` / `GET /health`
  - **Description**: Returns backend health status and application version.
  - **Response**: `{"status": "online", "app": "Shield AI", "version": "1.0.0"}`

### **Authentication (`/auth`)**
- `POST /auth/register`: User registration with hashed passwords (`bcrypt`).
- `POST /auth/login`: User login returning JWT `access_token` and user object.
- `GET /auth/me`: Fetches authenticated profile using `Bearer` token.

### **Threads & Conversations (`/api/threads`)**
- `POST /api/threads`
  - **Description**: Creates a new thread assigned to the authenticated user.
  - **Response**: `{"id": "uuid", "user_id": 1, "title": "New conversation", "created_at": "...", "updated_at": "..."}`
- `GET /api/threads`
  - **Description**: Returns all threads belonging to the current user, sorted by `updated_at DESC`.
- `GET /api/threads/{thread_id}`
  - **Description**: Returns metadata for a specific thread owned by the user.
- `GET /api/threads/{thread_id}/messages`
  - **Description**: Returns chronological chat history (`created_at ASC`) for the selected thread.
- `DELETE /api/threads/{thread_id}`
  - **Description**: Deletes a conversation thread and its associated messages.

### **Agent Chat (`/api/chat`)**
- `POST /api/chat`
  - **Request**: `{"thread_id": "uuid", "message": "User query text"}`
  - **Flow**:
    1. Authenticates request via JWT header.
    2. Enforces thread ownership check (`WHERE thread_id = :id AND user_id = :user_id`).
    3. Saves user message to SQLite `messages` table.
    4. Formats user's long-term memory into prompt context.
    5. Invokes LangGraph ReAct agent (binding ChromaDB RAG, Ollama Vision, Calculator, and MCP tools).
    6. Persists assistant response message to SQLite.
    7. Schedules non-blocking background tasks:
       - **Automated Title Generation** (for new threads after first user message).
       - **Long-Term Memory Extraction** (identifies durable user preferences/facts).
  - **Response**: `{"thread_id": "uuid", "message": "Assistant response text", "title": "Updated Title"}`

### **Long-Term User Memory (`/api/memory`)**
- `GET /api/memory`: Returns user's long-term memories (`memory_key`, `memory_value`).
- `DELETE /api/memory/{memory_id}`: Deletes a user memory record.

### **Knowledge Base RAG Upload (`/api/upload`)**
- `POST /api/upload`: Ingests PDF or text documents into ChromaDB vector store.

---

## 3. Frontend API Client Layer (`frontend/src/api/chat.js`)

Created `frontend/src/api/chat.js` for clean integration with React components:

```javascript
import { createThread, fetchThreads, fetchThreadMessages, deleteThread, sendMessage, fetchMemories, deleteMemory } from './api/chat';

// Example: Sending message in thread
const response = await sendMessage(token, activeThreadId, "Explain FastAPI & Ollama");

// Example: Fetching user threads for sidebar
const threads = await fetchThreads(token);
```

---

## 4. Security & User Isolation Enforcements

1. **Authentication Dependency (`get_current_user`)**:
   `user_id` is never accepted from incoming frontend JSON payloads or query parameters. The user identity is strictly extracted from the JWT token.

2. **Database Query Scoping**:
   All database operations enforce user ownership:
   ```python
   db.query(Conversation).filter(
       Conversation.id == thread_id,
       Conversation.user_id == current_user.id
   ).first()
   ```

3. **CORS Configuration**:
   Configured with explicit allowed origins (`FRONTEND_URL` env variable, `http://localhost:5173`, `http://127.0.0.1:5173`).

---

## 5. Separation of Storage Layers

- **SQLite Database (`./data/app.db`)**: Holds application-level tables (`users`, `conversations`, `messages`, `long_term_memories`).
- **ChromaDB Vector Store (`./chroma_db`)**: Holds document chunks and embeddings for RAG search.
- **SQLite Checkpointer (`./data/checkpoints.db`)**: Holds persistent agent execution state using `SqliteSaver`.

---

## 6. How to Run the System

### **Start Backend**
```powershell
cd d:\sih\project\backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### **Start Frontend**
```powershell
cd d:\sih\project\frontend
npm run dev
```

---

## 7. Frontend Chat Component Integration

To resolve the inability to chat from the frontend, the following UI components and state management flows were updated while strictly preserving design aesthetics:

1. **`frontend/src/api/chat.js`**:
   - Implemented API methods (`createThread`, `fetchThreads`, `fetchThreadMessages`, `deleteThread`, `sendMessage`, `fetchMemories`, `deleteMemory`, `uploadDocument`) to wrap backend calls with JWT Authorization header.

2. **`frontend/src/components/chat/ChatInput.jsx`**:
   - Added file selection handler on `<Plus />` button (`.pdf`, `.txt`, `.md`).
   - Added `onSendMessage` callback listener to `<textarea>` (`Enter` key without `Shift`).
   - Connected `ArrowUp` submit button to submit user text and toggle loading spinner (`Loader2`).

3. **`frontend/src/components/chat/ChatMessageList.jsx`**:
   - Created message history renderer displaying User and Assistant bubbles with avatar badges and automatic scrolling (`bottomRef.scrollIntoView`).

4. **`frontend/src/components/layout/Sidebar.jsx`**:
   - Wired "Documents" navigation link to trigger document upload directly into ChromaDB.
   - Replaced static task array with dynamic `threads` list fetched from `/api/threads`.
   - Wired "New" thread button (`+ New`) and thread deletion (`Trash2` icon) to backend endpoints.

5. **`frontend/src/App.jsx`**:
   - Connected user authentication state with active thread state (`activeThreadId`), loading threads on startup, optimistic user message updates, sending user messages to `/api/chat`, and uploading documents to `/api/upload`.

