# Shield AI — Deep Agent Architecture Migration & Refactoring Specification

## ROLE

You are a senior Python/AI systems engineer specializing in:

* LangGraph
* LangChain
* Deep Agents
* MCP
* FastAPI
* Ollama
* RAG
* multimodal AI
* sandboxed code execution
* document generation
* SQLite/SQLAlchemy
* React streaming applications

You are modifying an **existing production-oriented project called Shield AI**.

Do NOT rebuild the project from scratch.

First inspect the existing repository, understand the current implementation, preserve working functionality, and incrementally refactor the architecture.

---

# 1. EXISTING PROJECT

Project:

```text
Shield AI
```

Mission:

> An enterprise-grade sovereign, local-first AI assistant and document intelligence platform operating entirely on-premise/offline.

Current major components:

```text
React 19 + Vite
FastAPI
LangChain
LangGraph
Ollama
ministral-3:3b
embeddinggemma
ChromaDB
SQLite
SQLAlchemy
JWT
MCP
mcp-docgen
SSE streaming
```

Current capabilities already include:

* authentication
* user accounts
* conversation threads
* persistent messages
* long-term memory
* LangGraph checkpoints
* RAG
* image analysis
* calculator
* document generation
* MCP document generation
* streaming responses
* document downloads
* React ChatGPT-like UI

Preserve these capabilities.

---

# 2. PRIMARY OBJECTIVE

Transform the current Shield AI architecture into a proper:

```text
Supervisor Deep Agent
        +
Specialized Subagents
        +
Skills
        +
MCP
        +
Composite Backend
        +
StateBackend
        +
StoreBackend
        +
FilesystemBackend
        +
Sandboxed Code Execution
        +
RAG
        +
Vision
        +
Document Generation
        +
Verification / Self-Correction
```

The final system should behave like an enterprise local-first agentic workspace.

The main agent should not directly perform every task.

Instead:

```text
USER
 ↓
MAIN DEEP AGENT
 ↓
PLAN
 ↓
SELECT SKILLS
 ↓
DELEGATE
 ↓
SPECIALIZED SUBAGENTS
 ↓
TOOLS / MCP / SANDBOX
 ↓
VERIFY
 ↓
FIX IF REQUIRED
 ↓
FINAL RESULT
```

---

# 3. IMPORTANT MIGRATION RULE

DO NOT unnecessarily rewrite:

```text
authentication
database models
thread APIs
message APIs
frontend UI
SSE protocol
Ollama integration
RAG storage
existing MCP integration
existing document tools
```

Reuse them wherever possible.

The goal is:

```text
existing Shield AI
        ↓
architectural evolution
        ↓
Deep Agent based Shield AI
```

not:

```text
delete everything
        ↓
new project
```

Before modifying anything:

1. inspect the repository
2. inspect current agent implementation
3. inspect current tools
4. inspect MCP client
5. inspect RAG implementation
6. inspect database models
7. inspect streaming implementation
8. inspect document generation
9. inspect frontend integration
10. identify reusable components
11. identify architectural conflicts
12. create a migration plan

Do not make changes until the current architecture is understood.

---

# 4. TARGET ARCHITECTURE

Implement this architecture:

```text
                         ┌──────────────────────┐
                         │       React UI       │
                         │ React 19 + Vite      │
                         └──────────┬───────────┘
                                    │
                              HTTP / SSE
                                    │
                         ┌──────────▼───────────┐
                         │       FastAPI        │
                         │ API / Auth / Threads │
                         └──────────┬───────────┘
                                    │
                                    ▼
                     ┌────────────────────────────┐
                     │      MAIN DEEP AGENT       │
                     │       SUPERVISOR           │
                     │                            │
                     │ Understand                 │
                     │ Plan                       │
                     │ Delegate                   │
                     │ Coordinate                 │
                     │ Verify                     │
                     └─────────────┬──────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
   Research Agent             RAG Agent              Vision Agent
          │                        │                        │
          ▼                        ▼                        ▼
        MCP                    ChromaDB                  Ollama
                                   │
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
   Coding Agent             Document Agent        Verification Agent
          │                        │                        │
          ▼                        ▼                        ▼
      Sandbox                 Skills + Python         Inspect/Test
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  MCP TOOL LAYER │
                          └────────┬────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │ CompositeBackend  │
                         └─────────┬─────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
          StateBackend       StoreBackend    FilesystemBackend
                 │                 │                 │
                 ▼                 ▼                 ▼
          Current State      Long Memory       Actual Files
          Thread State       User Memory       Workspace
          Agent State        Project Memory    Uploads
```

---

# 5. MAIN DEEP AGENT

Create a dedicated main supervisor agent.

Suggested location:

```text
backend/app/agent/
```

Structure:

```text
agent/
├── __init__.py
├── main_agent.py
├── state.py
├── prompts.py
├── router.py
├── planner.py
├── delegation.py
└── config.py
```

The Main Agent must be responsible for:

### A. Understanding

Interpret the user's request.

### B. Planning

Create an explicit execution plan for complex tasks.

### C. Delegation

Delegate tasks to specialized agents.

### D. Coordination

Combine subagent results.

### E. Verification

Ensure generated artifacts and important operations are valid.

### F. Iteration

If something fails:

```text
failure
 ↓
diagnose
 ↓
delegate fix
 ↓
execute
 ↓
verify again
```

The Main Agent should not directly implement specialized tasks when a suitable subagent exists.

---

# 6. SUBAGENTS

Create the following specialized agents.

```text
backend/app/agent/subagents/

├── research_agent.py
├── rag_agent.py
├── vision_agent.py
├── coding_agent.py
├── document_agent.py
└── verification_agent.py
```

---

# 7. RESEARCH AGENT

Responsibilities:

* research
* information gathering
* MCP search
* source analysis
* structured research
* summarization

It should use MCP tools where appropriate.

Do not hard-code web functionality into the Main Agent.

The Main Agent should delegate:

```text
"Research X"
```

to:

```text
Research Agent
```

---

# 8. RAG AGENT

Reuse the existing:

```text
app/rag.py
```

implementation where possible.

Refactor it behind a dedicated RAG agent.

Responsibilities:

* search uploaded documents
* retrieve relevant chunks
* thread-scoped retrieval
* user-scoped retrieval
* document-grounded answering
* metadata filtering

Architecture:

```text
User Query
    ↓
RAG Agent
    ↓
Retriever
    ↓
ChromaDB
    ↓
embeddinggemma
    ↓
Relevant chunks
    ↓
RAG Agent
    ↓
Main Agent
```

Preserve:

```text
thread_id
user_id
```

isolation.

A user must never retrieve another user's private data.

---

# 9. VISION AGENT

Reuse the existing:

```text
app/vision.py
```

implementation.

Create:

```text
vision_agent.py
```

Responsibilities:

* image analysis
* scanned documents
* charts
* diagrams
* screenshots
* photos
* handwritten content
* visual document understanding

Use local Ollama vision inference.

The Vision Agent should be callable by the Main Agent.

Example:

```text
Main Agent
    ↓
Vision Agent
    ↓
Ollama Vision
    ↓
Structured result
    ↓
Main Agent
```

---

# 10. CODING AGENT

Create a dedicated Coding Agent.

Location:

```text
backend/app/agent/subagents/coding_agent.py
```

Responsibilities:

* write code
* inspect code
* modify code
* execute code
* debug
* test
* fix execution failures
* generate scripts
* automate tasks

CRITICAL:

Do NOT execute arbitrary generated Python directly on the FastAPI host process.

All generated code must execute inside an isolated sandbox.

Architecture:

```text
Coding Agent
      ↓
Generate Python
      ↓
Sandbox
      ↓
Execute
      ↓
stdout/stderr
      ↓
Coding Agent
      ↓
Success?
   /       \
 yes       no
  |         |
  |       diagnose
  |         |
  |        fix
  |         |
  |       execute
  |         |
  └───────┘
```

---

# 11. SANDBOX

Create:

```text
backend/app/sandbox/
```

with:

```text
sandbox/
├── __init__.py
├── executor.py
├── docker_executor.py
├── security.py
└── models.py
```

Initially support Docker-based execution if available.

The sandbox should:

* isolate generated code
* limit filesystem access
* restrict network access by default
* impose execution timeout
* capture stdout
* capture stderr
* return exit code
* return generated artifacts
* prevent access to application secrets
* prevent access to arbitrary host paths

Example API:

```python
result = await sandbox.execute(
    code=python_code,
    workspace="/workspace",
    timeout=120,
)
```

Return structured information:

```python
{
    "success": True,
    "exit_code": 0,
    "stdout": "...",
    "stderr": "",
    "artifacts": [...]
}
```

---

# 12. DOCUMENT AGENT

This is a critical architectural requirement.

Do NOT implement document generation as a giant collection of hard-coded LLM tools.

Instead use:

```text
Document Agent
      ↓
Read Skill
      ↓
Generate Python
      ↓
Coding Agent
      ↓
Sandbox
      ↓
Create document
      ↓
Verification Agent
```

The Document Agent should support:

```text
DOCX
PDF
PPTX
XLSX
CSV
HTML
```

---

# 13. SKILL SYSTEM

Create a real skill system.

Recommended structure:

```text
backend/skills/

├── documents/
│   ├── SKILL.md
│   │
│   ├── docx/
│   │   └── SKILL.md
│   │
│   ├── pdf/
│   │   └── SKILL.md
│   │
│   ├── pptx/
│   │   └── SKILL.md
│   │
│   ├── xlsx/
│   │   └── SKILL.md
│   │
│   ├── csv/
│   │   └── SKILL.md
│   │
│   └── html/
│       └── SKILL.md
│
├── coding/
│   └── SKILL.md
│
├── rag/
│   └── SKILL.md
│
├── vision/
│   └── SKILL.md
│
├── research/
│   └── SKILL.md
│
└── verification/
    └── SKILL.md
```

Skills should be loaded on demand.

Do not inject every skill into every prompt.

---

# 14. DOCUMENT SKILL EXECUTION

For every document request:

```text
User:
Create a Word report.
```

The system should:

```text
Main Agent
    ↓
Document Agent
    ↓
Read documents/SKILL.md
    ↓
Read documents/docx/SKILL.md
    ↓
Understand requirements
    ↓
Generate Python
    ↓
Send Python to Coding Agent
    ↓
Coding Agent executes in Sandbox
    ↓
DOCX generated
    ↓
Verification Agent
    ↓
PASS / FAIL
```

If FAIL:

```text
Verification Agent
      ↓
Failure report
      ↓
Coding Agent
      ↓
Fix Python
      ↓
Sandbox
      ↓
Regenerate
      ↓
Verify
```

Never return an artifact merely because Python exited successfully.

The generated artifact must be validated.

---

# 15. DOCUMENT LIBRARIES

Use appropriate libraries inside the sandbox.

DOCX:

```text
python-docx
```

XLSX:

```text
openpyxl
```

PDF:

```text
reportlab
PyMuPDF where required
```

PPTX:

```text
python-pptx
```

CSV:

```text
pandas
```

HTML:

```text
standard Python / templating
```

The skill should tell the agent which library and methodology to use.

---

# 16. DOCUMENT VERIFICATION

Create:

```text
verification_agent.py
```

It should inspect generated artifacts.

For DOCX:

* file exists
* opens successfully
* expected headings exist
* expected text exists
* tables exist if requested
* document is non-empty

For XLSX:

* workbook opens
* required sheets exist
* expected headers exist
* formulas are valid where applicable

For PPTX:

* presentation opens
* expected slide count
* expected titles
* no malformed slides

For PDF:

* file opens
* page count
* expected text
* basic structural validation

For HTML:

* valid file
* expected sections
* required content

Return:

```python
{
    "status": "PASS",
    "artifact": "...",
    "checks": [...]
}
```

or:

```python
{
    "status": "FAIL",
    "errors": [...]
}
```

---

# 17. COMPOSITE BACKEND

Implement a Composite Backend architecture.

The conceptual routing should be:

```text
CompositeBackend
│
├── StateBackend
│
├── StoreBackend
│
└── FilesystemBackend
```

Use the current installed/compatible Deep Agents backend APIs rather than inventing incompatible APIs.

Before implementing this portion, inspect the installed Deep Agents/LangChain version and its current backend interfaces.

Do not blindly copy an outdated API example.

---

# 18. STATEBACKEND

StateBackend is for thread-scoped execution state.

Use it for:

```text
current plan
current task
subagent results
temporary state
agent execution state
intermediate reasoning state
```

Do NOT use it as the permanent user memory store.

---

# 19. STOREBACKEND

StoreBackend is for persistent information.

Use it for:

```text
user memory
project memory
persistent preferences
agent memory
reusable workflow information
persistent skill metadata
```

The existing:

```text
long_term_memories
```

table should remain compatible.

If appropriate, create an adapter between the current SQLAlchemy memory repository and the Deep Agent Store abstraction rather than deleting the existing memory API.

Existing endpoints must continue working:

```text
GET    /api/memory
DELETE /api/memory/{id}
```

---

# 20. FILESYSTEM BACKEND

Use FilesystemBackend for actual workspace files.

Recommended workspace:

```text
backend/workspace/
│
├── users/
│   └── {user_id}/
│       ├── uploads/
│       ├── projects/
│       ├── generated/
│       ├── code/
│       ├── temporary/
│       └── artifacts/
```

Do not use one global unrestricted workspace for all users.

All paths must be user-scoped.

---

# 21. USER DATA ISOLATION

This is mandatory.

Every operation involving:

```text
files
memory
RAG
threads
documents
artifacts
workspace
```

must respect:

```text
user_id
```

and where applicable:

```text
thread_id
```

Never allow:

```text
User A
   ↓
User B files
```

or:

```text
User A
   ↓
User B Chroma documents
```

or:

```text
User A
   ↓
User B memories
```

---

# 22. MCP INTEGRATION

Preserve the existing:

```text
app/mcp/mcp_client.py
```

and existing `mcp-docgen` integration.

Refactor it so MCP becomes a first-class tool provider for the Deep Agent.

Architecture:

```text
Main Agent
     │
     ▼
MCP Adapter
     │
     ├── Document MCP
     ├── Search MCP
     ├── Internal MCP
     ├── Database MCP
     └── Other local MCP servers
```

Use the currently installed compatible LangChain MCP adapter APIs.

Do not hard-code outdated APIs.

---

# 23. MCP + SKILLS

Maintain a clear separation.

```text
SKILL
=
How to perform a task
```

```text
MCP
=
Capability/tool access
```

```text
BACKEND
=
Storage/state
```

```text
SANDBOX
=
Safe execution
```

```text
AGENT
=
Reasoning/orchestration
```

Example:

```text
DOCX request

Skill:
How should a professional DOCX be generated?

MCP:
What document-related capabilities are available?

Coding Agent:
Generate Python.

Sandbox:
Execute Python safely.

FilesystemBackend:
Store output.

Verification Agent:
Validate output.
```

---

# 24. EXISTING MCP NEWLINE BUG

Preserve the previous solution for the Ollama/MCP newline issue.

The current system had:

```text
invalid character '\n' in string literal
```

Ensure MCP tool descriptions and tool schemas are sanitized where required.

Continue using safe single-line descriptions where Ollama's tool-call serialization requires it.

Also ensure generated tool arguments are valid JSON.

Do not reintroduce the old bug during refactoring.

---

# 25. DOCUMENT GENERATION ARCHITECTURE

The final document workflow must be:

```text
                 DOCUMENT REQUEST
                        │
                        ▼
                  MAIN AGENT
                        │
                        ▼
                 DOCUMENT AGENT
                        │
                        ▼
                  LOAD SKILLS
                        │
                        ▼
                CREATE PLAN
                        │
                        ▼
                GENERATE PYTHON
                        │
                        ▼
                  CODING AGENT
                        │
                        ▼
                    SANDBOX
                        │
                        ▼
                 CREATE ARTIFACT
                        │
                        ▼
               VERIFICATION AGENT
                        │
                 ┌──────┴──────┐
                 ▼             ▼
                PASS          FAIL
                 │             │
                 ▼             ▼
              RETURN         FIX
                               │
                               ▼
                             EXECUTE
                               │
                               ▼
                             VERIFY
```

---

# 26. EXAMPLE: DOCX

Request:

```text
Create a 20-page technical report.
```

Expected internal workflow:

```text
Main Agent
 ↓
Document Agent
 ↓
RAG Agent
 ↓
retrieve source information
 ↓
Document Agent
 ↓
read:
  documents/SKILL.md
  documents/docx/SKILL.md
 ↓
generate Python
 ↓
Coding Agent
 ↓
Sandbox
 ↓
python-docx
 ↓
report.docx
 ↓
Verification Agent
 ↓
PASS
```

---

# 27. EXAMPLE: EXCEL

Request:

```text
Analyze this CSV and create an Excel dashboard.
```

Workflow:

```text
Main Agent
 ↓
RAG/Data Agent
 ↓
inspect CSV
 ↓
Document Agent
 ↓
read XLSX skill
 ↓
generate Python
 ↓
Coding Agent
 ↓
Sandbox
 ↓
pandas + openpyxl
 ↓
dashboard.xlsx
 ↓
Verification
 ↓
PASS
```

---

# 28. EXAMPLE: MULTIMODAL PDF

Request:

```text
Analyze this scanned engineering PDF and create a report.
```

Workflow:

```text
PDF
 ↓
Vision Agent
 ↓
OCR / VLM
 ↓
structured visual information
 ↓
RAG Agent
 ↓
indexed knowledge
 ↓
Main Agent
 ↓
Document Agent
 ↓
DOCX Skill
 ↓
Python
 ↓
Sandbox
 ↓
DOCX
 ↓
Verification
```

---

# 29. MEMORY ARCHITECTURE

Preserve the current autonomous memory extraction.

Current:

```text
messages
 ↓
memory extraction LLM
 ↓
long_term_memories
```

Integrate it with the new architecture:

```text
Conversation
     ↓
Main Agent
     ↓
Memory Extraction
     ↓
StoreBackend
     │
     └── SQLAlchemy persistence
```

The memory system must remain user-scoped.

Do not store sensitive temporary reasoning as long-term memory.

Only durable information should be persisted.

---

# 30. CHECKPOINTING

Preserve:

```text
AsyncSqliteSaver
```

for LangGraph checkpoints.

Use it for:

```text
thread execution state
agent continuation
tool calls
subagent execution
multi-turn state
```

Do not confuse:

```text
checkpoint
```

with:

```text
long-term memory
```

Checkpoint:

```text
What was happening in this execution?
```

Memory:

```text
What should the system remember about the user/project?
```

---

# 31. EXISTING DATABASE

Preserve:

```text
users
conversations
messages
long_term_memories
```

Do not remove existing tables.

If additional metadata is required, use migrations.

Potential new entities may include:

```text
artifacts
agent_runs
tool_executions
```

but only add them when genuinely needed.

Do not duplicate existing message/thread functionality.

---

# 32. ARTIFACT SYSTEM

Create a unified artifact representation.

Example:

```python
Artifact(
    id="...",
    user_id="...",
    thread_id="...",
    filename="report.docx",
    file_type="docx",
    path="...",
    size=12345,
    created_at=...,
    verification_status="passed",
)
```

The frontend should be able to display:

```text
Generated document

report.docx

[Download]
```

The existing secure document download endpoint should continue to work.

---

# 33. TOOL EXECUTION EVENTS

Extend the existing SSE system without breaking compatibility.

Current events:

```text
init
token
done
error
```

Add optional events:

```text
plan
subagent_start
subagent_result
tool_start
tool_result
artifact_created
verification
```

Example:

```text
data: {
  "type": "subagent_start",
  "agent": "document_agent"
}
```

Then:

```text
data: {
  "type": "tool_start",
  "tool": "execute_python"
}
```

Then:

```text
data: {
  "type": "artifact_created",
  "filename": "report.docx"
}
```

Finally:

```text
data: {
  "type": "verification",
  "status": "passed"
}
```

The frontend should gracefully ignore unknown events until the UI is updated.

Do not break existing token streaming.

---

# 34. FRONTEND

Do not rebuild the frontend.

Preserve:

```text
ChatInput
ChatMessageList
MarkdownMessage
MessageActions
ToolExecution
AttachmentMenu
ChatComposer
Sidebar
TopBar
StreamingController
useChatState
useAutoScroll
```

Extend the UI to optionally show:

```text
Planning
Researching
Using RAG
Running Vision
Calling MCP
Writing code
Executing code
Generating document
Verifying document
```

These should appear as collapsible execution status components.

Do NOT expose private chain-of-thought.

Show only concise execution status.

Example:

```text
✓ Read document skill
✓ Analyzed source PDFs
✓ Generated report
✓ Verified DOCX

report.docx
[Download]
```

---

# 35. STREAMING PERFORMANCE

Preserve the existing:

```text
requestAnimationFrame
```

token batching system.

Do not replace it with per-token React state updates.

Preserve:

```text
AbortController
SSE
directional auto-scroll
jump-to-latest
```

Streaming must remain responsive while agents execute tools.

---

# 36. CHAT MODES

The existing mode selector can be extended to:

```text
Normal
Deep Agent
RAG
Vision
Research
Coding
Document
```

However, the Main Agent should normally be able to automatically determine the required capability.

Modes should be hints/constraints rather than completely separate implementations.

---

# 37. SECURITY REQUIREMENTS

The new architecture must preserve sovereign/local-first operation.

No required cloud API.

Default AI execution:

```text
Ollama
 ↓
Local models
```

No external data transfer unless explicitly configured.

Sandbox security:

* no host filesystem escape
* no secrets
* timeout
* restricted network
* user workspace isolation
* safe subprocess execution

Document download:

* prevent `../`
* canonicalize paths
* enforce workspace root
* enforce user ownership

MCP:

* only configured servers
* validate tool calls
* avoid arbitrary command execution through MCP

---

# 38. OFFLINE-FIRST REQUIREMENT

The entire system should work without Internet connectivity for core capabilities:

```text
Chat
RAG
Vision
Memory
Document generation
Coding
Sandbox execution
MCP local servers
```

External research should be considered an optional MCP capability rather than a required dependency.

---

# 39. MODEL CONFIGURATION

Preserve configuration:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=ministral-3:3b
VISION_MODEL=ministral-3:3b
EMBEDDING_MODEL=embeddinggemma
```

Do not hard-code model names.

Create model abstraction/configuration so models can later be changed to:

```text
Qwen
Llama
Mistral
Gemma
other Ollama models
```

without rewriting the agent architecture.

---

# 40. LANGGRAPH DESIGN

Use LangGraph as the execution/state orchestration layer.

Conceptually:

```text
START
  ↓
INTAKE
  ↓
PLAN
  ↓
ROUTE
  ↓
DELEGATE
  ↓
EXECUTE
  ↓
VERIFY
  ↓
SUCCESS?
 /     \
YES     NO
 |       |
END     FIX
         |
         └────→ EXECUTE
```

Subagents may themselves use agent loops.

Example:

```text
Main Graph
    │
    ├── RAG Subagent
    │
    ├── Coding Subagent
    │
    ├── Document Subagent
    │
    └── Vision Subagent
```

Use appropriate Deep Agent APIs for subagent creation.

Do not manually recreate functionality already provided by the installed Deep Agents framework.

---

# 41. DEEP AGENT BACKEND

Use the installed Deep Agents version as the source of truth.

Before implementation:

1. inspect installed package version
2. inspect available backend classes
3. inspect `create_deep_agent`
4. inspect subagent APIs
5. inspect skill loading APIs
6. inspect backend interfaces
7. inspect MCP adapter compatibility

Do not assume an API from an old tutorial.

If APIs differ from this specification, adapt the implementation to the installed/current APIs while preserving the architecture.

---

# 42. SKILL LOADING

Skills should be loaded dynamically.

Example conceptual flow:

```text
User:
Create Excel dashboard

        ↓

Main Agent

        ↓

Document Agent

        ↓

Read:
skills/documents/SKILL.md
skills/documents/xlsx/SKILL.md

        ↓

Generate Python

        ↓

Sandbox
```

Do not inject:

```text
DOCX
PDF
PPTX
XLSX
RAG
Vision
Coding
Research
```

skills into every request.

Only load relevant skills.

---

# 43. DELETE OPERATIONS

Because FilesystemBackend operations can potentially be destructive:

Implement safety rules around:

```text
delete
overwrite
recursive directory deletion
```

For user-requested deletion:

```text
confirm scope
validate path
ensure user ownership
execute deletion
```

Never allow an agent to recursively delete arbitrary filesystem paths.

---

# 44. TESTING

Create tests for:

### Agent

```text
main agent routing
subagent delegation
planning
verification
```

### RAG

```text
user isolation
thread isolation
retrieval
embedding
```

### Documents

```text
DOCX generation
XLSX generation
PPTX generation
PDF generation
HTML generation
```

### Sandbox

```text
execution
timeout
failure handling
filesystem restrictions
```

### MCP

```text
tool discovery
tool invocation
malformed tool arguments
newline sanitization
```

### Streaming

Preserve current tests and add:

```text
tool events
subagent events
artifact events
verification events
```

---

# 45. MIGRATION PHASES

Implement in phases.

## Phase 1 — Repository Analysis

Do not modify code.

Inspect:

```text
agent.py
tools.py
rag.py
vision.py
memory.py
database.py
repositories.py
mcp_client.py
routers
frontend streaming
```

Create:

```text
MIGRATION_PLAN.md
```

containing:

* current architecture
* target architecture
* files to reuse
* files to refactor
* files to create
* compatibility concerns
* dependencies required
* migration order

---

## Phase 2 — Agent Package

Create:

```text
app/agent/
```

Implement:

```text
main_agent
state
planner
delegation
subagents
```

Keep the old agent temporarily available if necessary.

---

## Phase 3 — Skills

Create the skill hierarchy.

Start with:

```text
documents
docx
xlsx
pptx
pdf
html
coding
rag
vision
verification
```

---

## Phase 4 — Sandbox

Implement isolated Python execution.

Test it independently before connecting it to the Document Agent.

---

## Phase 5 — Composite Backend

Implement:

```text
StateBackend
StoreBackend
FilesystemBackend
CompositeBackend
```

Integrate it with Deep Agents using the currently installed API.

---

## Phase 6 — Subagents

Implement:

```text
Research
RAG
Vision
Coding
Document
Verification
```

---

## Phase 7 — MCP

Integrate existing MCP tools with the new Main Agent/Subagents.

Preserve existing `mcp-docgen`.

---

## Phase 8 — Document Pipeline

Implement:

```text
Skill
 ↓
Python
 ↓
Sandbox
 ↓
Artifact
 ↓
Verification
```

for:

```text
DOCX
XLSX
PPTX
PDF
HTML
```

---

## Phase 9 — FastAPI Integration

Replace the old agent execution path with the new Main Agent while preserving:

```text
/api/chat
/api/chat/stream
```

and existing authentication/thread behavior.

---

## Phase 10 — Frontend

Add execution-status events and artifact rendering without breaking current streaming.

---

## Phase 11 — Testing

Run:

```text
backend tests
agent tests
RAG tests
sandbox tests
document tests
MCP tests
frontend tests
```

Then perform end-to-end testing.

---

# 46. ACCEPTANCE TESTS

The migration is complete only when these scenarios work.

### Test 1 — Normal Chat

```text
Hello, explain RAG.
```

Expected:

```text
Main Agent
 ↓
answer
 ↓
stream response
```

---

### Test 2 — RAG

Upload:

```text
company.pdf
```

Then ask:

```text
What does the document say about safety procedures?
```

Expected:

```text
Main Agent
 ↓
RAG Agent
 ↓
Chroma
 ↓
answer grounded in document
```

---

### Test 3 — Vision

Upload image.

Ask:

```text
Analyze this diagram.
```

Expected:

```text
Main Agent
 ↓
Vision Agent
 ↓
Ollama Vision
 ↓
answer
```

---

### Test 4 — DOCX

```text
Create a professional report about the uploaded PDF.
```

Expected:

```text
Main Agent
 ↓
RAG Agent
 ↓
Document Agent
 ↓
DOCX Skill
 ↓
Python
 ↓
Coding Agent
 ↓
Sandbox
 ↓
report.docx
 ↓
Verification
 ↓
PASS
 ↓
Download
```

---

### Test 5 — XLSX

```text
Create an Excel analysis of this dataset.
```

Expected:

```text
XLSX Skill
 ↓
Python
 ↓
openpyxl
 ↓
Sandbox
 ↓
analysis.xlsx
 ↓
Verification
```

---

### Test 6 — Failed Code

Force generated Python to fail.

Expected:

```text
Sandbox
 ↓
ERROR
 ↓
Coding Agent
 ↓
Fix
 ↓
Sandbox
 ↓
SUCCESS
 ↓
Verification
```

---

### Test 7 — MCP

Call an MCP document-generation tool.

Expected:

```text
Main Agent
 ↓
MCP
 ↓
tool
 ↓
result
 ↓
agent continues
```

---

### Test 8 — Memory

Tell the system a durable preference.

Then create a new thread.

Expected:

```text
Memory Extraction
 ↓
StoreBackend / existing memory persistence
 ↓
new thread
 ↓
memory retrieved
```

---

### Test 9 — User Isolation

Create two users.

Verify:

```text
User A cannot access User B:
- files
- RAG chunks
- memories
- artifacts
- threads
```

---

# 47. DO NOT DO THESE THINGS

Do NOT:

1. rebuild the application from scratch
2. remove working authentication
3. remove existing thread APIs
4. remove SSE streaming
5. remove ChromaDB
6. remove Ollama
7. replace local models with cloud models
8. execute generated code directly on the FastAPI host
9. expose unrestricted shell access
10. mix all users into one workspace
11. inject every skill into every prompt
12. hard-code every document format as a separate LLM tool
13. expose chain-of-thought to the frontend
14. delete existing functionality without migration
15. use outdated Deep Agents APIs without checking installed versions
16. introduce unnecessary infrastructure such as Redis/Celery unless required
17. break existing API contracts unnecessarily

---

# 48. TARGET FINAL DIRECTORY

Evolve the current repository toward:

```text
backend/
│
├── app/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── repositories/
│   │
│   ├── agent/
│   │   ├── main_agent.py
│   │   ├── planner.py
│   │   ├── delegation.py
│   │   ├── state.py
│   │   │
│   │   └── subagents/
│   │       ├── research_agent.py
│   │       ├── rag_agent.py
│   │       ├── vision_agent.py
│   │       ├── coding_agent.py
│   │       ├── document_agent.py
│   │       └── verification_agent.py
│   │
│   ├── backends/
│   │   ├── composite.py
│   │   ├── state.py
│   │   ├── store.py
│   │   └── filesystem.py
│   │
│   ├── sandbox/
│   │   ├── executor.py
│   │   ├── docker_executor.py
│   │   └── security.py
│   │
│   ├── mcp/
│   │   ├── mcp_client.py
│   │   └── adapters.py
│   │
│   ├── rag/
│   │   ├── ingestion.py
│   │   ├── retrieval.py
│   │   └── embeddings.py
│   │
│   ├── verification/
│   │   ├── artifact.py
│   │   ├── document.py
│   │   └── code.py
│   │
│   ├── agent.py              # compatibility wrapper during migration
│   ├── memory.py
│   ├── vision.py
│   ├── rag.py                # compatibility layer if needed
│   ├── tools.py              # legacy/shared tools during migration
│   ├── database.py
│   └── config.py
│
├── skills/
│   ├── documents/
│   │   ├── SKILL.md
│   │   ├── docx/SKILL.md
│   │   ├── pdf/SKILL.md
│   │   ├── pptx/SKILL.md
│   │   ├── xlsx/SKILL.md
│   │   ├── csv/SKILL.md
│   │   └── html/SKILL.md
│   ├── coding/SKILL.md
│   ├── rag/SKILL.md
│   ├── vision/SKILL.md
│   ├── research/SKILL.md
│   └── verification/SKILL.md
│
├── workspace/
│   └── users/
│
├── uploads/
├── data/
│   ├── app.db
│   └── checkpoints.db
│
└── tests/
```

---

# 49. FINAL BEHAVIOR

After migration, Shield AI should behave like this:

```text
                    SHIELD AI
                        │
                        ▼
                  Main Deep Agent
                        │
                  ┌─────┴─────┐
                  │   PLAN    │
                  └─────┬─────┘
                        │
                        ▼
                 Select capability
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
        RAG          Vision        Coding
          │             │             │
          └─────────────┼─────────────┘
                        │
                        ▼
                    Document
                     Agent
                        │
                     Skills
                        │
                    Python
                        │
                    Sandbox
                        │
                    Artifact
                        │
                  Verification
                        │
                ┌───────┴───────┐
                │               │
              PASS             FAIL
                │               │
                ▼               ▼
             RETURN            FIX
                                │
                                ▼
                              RETRY
                                │
                                ▼
                             VERIFY
```

The result should be a **local-first Deep Agent platform**, not merely a chatbot with additional tools.

---

# 50. IMPLEMENTATION RULE

Work incrementally.

For each phase:

1. inspect existing implementation
2. explain what will change
3. implement
4. run tests
5. fix errors
6. verify compatibility
7. continue to next phase

Do not make a massive unverified rewrite.

At every stage preserve the ability to start:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

and:

```bash
cd frontend
npm run dev
```

The final application must preserve all existing Shield AI functionality while adding the new Deep Agent architecture.

## FINAL SUCCESS CRITERIA

The completed Shield AI system must provide:

```text
✓ Local Ollama LLM
✓ Local vision
✓ Local embeddings
✓ RAG
✓ Persistent threads
✓ Long-term memory
✓ LangGraph checkpoints
✓ Main Deep Agent
✓ Specialized subagents
✓ Dynamic skills
✓ MCP integration
✓ Composite Backend
✓ StateBackend
✓ StoreBackend
✓ FilesystemBackend
✓ Sandboxed code execution
✓ DOCX generation
✓ XLSX generation
✓ PPTX generation
✓ PDF generation
✓ HTML generation
✓ Artifact verification
✓ Automatic correction loop
✓ User/file/RAG isolation
✓ SSE streaming
✓ React ChatGPT-like UI
✓ Offline-first operation
✓ Existing APIs preserved
```

The architectural principle is:

```text
                 SHIELD AI

        ┌──────────────────────────┐
        │      MAIN DEEP AGENT     │
        │    Brain / Supervisor    │
        └────────────┬─────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
     Skills         MCP       Subagents
        │            │            │
        └────────────┼────────────┘
                     │
                Backends
                     │
       ┌─────────────┼──────────────┐
       │             │              │
     State          Store       Filesystem
       │             │              │
       └─────────────┼──────────────┘
                     │
                  Sandbox
                     │
                  Artifacts
                     │
                Verification
                     │
                Self-correction
                     │
                  RESULT
```

**Do not expose internal chain-of-thought.** The UI should display only concise statuses, tool activity, artifacts, errors, and final results.
