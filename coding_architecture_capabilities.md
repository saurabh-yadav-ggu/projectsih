# Shield AI Coding Assistant — 4-Pillar Architecture Capabilities

This document details the complete implementation of the 11 capabilities across the 4 architectural pillars for the Shield AI Autonomous Coding Assistant:

```
EXECUTION ENVIRONMENT                 DELEGATION               STEERING
┌─────────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  ┌───────────────────┐
│ Code Interpreter│ │ Sandbox  │ │Filesystem│ │ Planning │ │ Subagents │  │ Human-in-the-loop │
└─────────────────┘ └──────────┘ └───┬──────┘ └──────────┘ └───────────┘  └───────────────────┘
                                     │
                      CONTEXT MANAGEMENT
                      ├─ Skills
                      ├─ Memory
                      ├─ Summarization
                      ├─ Context offloading
                      └─ Prompt caching
```

---

## Pillar 1: Execution Environment

### 1. Code Interpreter
- **Tool**: `code_interpreter(code: str) -> str` in [`backend/app/agent/coding_tools.py`](file:///d:/sih/project/backend/app/agent/coding_tools.py)
- **Functionality**:
  - Dynamically runs Python code within the active workspace.
  - Returns stdout, stderr, execution time (ms), and exit codes.
  - Automatically intercepts oversized terminal output (>200 lines or >8000 characters) and offloads to `.shield/scratch/` with a 40-line preview to prevent overflowing the LLM context window.

### 2. Sandbox
- **Engine**: [`backend/app/sandbox/executor.py`](file:///d:/sih/project/backend/app/sandbox/executor.py) (`SandboxExecutor`)
- **Security & Guards**:
  - AST-based static safety scanner: blocks destructive calls (`shutil.rmtree("/")`, `forkbomb`, malicious shell spawns).
  - Isolated subprocess execution jail bound to the selected workspace directory.
  - Wall-clock timeout enforcement (60 seconds) with process group termination on timeout.

### 3. Filesystem
- **Backend**: `LocalShellBackend` from `deepagents.backends`
- **Mount & Tools**:
  - The user's selected workspace directory is mounted as virtual root `/`.
  - Exposes `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, and `execute`.
  - Real-time `file_changed` protocol broadcasts update the React file tree and reload active editor tabs automatically.

---

## Pillar 2: Delegation

### 1. Planning
- **Tools**:
  - `create_plan(title: str, steps: List[str]) -> str`
  - `update_plan(step_index: int, status: str, notes: str) -> str`
- **Persistence**:
  - Written directly to `/.shield/PLAN.md` in the workspace root.
  - Maintains a milestone checklist (`- [ ]`, `- [/]`, `- [x]`) and progress notes.
  - The agent formulates plans before major architecture modifications and updates status in real-time.

### 2. Subagents
- **Framework**: `SubAgentMiddleware` via `task()` tool
- **Declarative Specialized Subagents**:
  1. `code-reviewer`: Analyzes code changes for logic flaws, security vulnerabilities, edge cases, and style guidelines.
  2. `code-researcher`: Uses `glob`, `grep`, and file inspection to trace dependencies, find symbols, and map architecture.
  3. `test-runner`: Generates and executes test suites using `pytest` or shell runners, diagnoses tracebacks, and verifies fixes.
- **Frontend Tracking**:
  - Emits `subagent_started` and `subagent_finished` events.
  - Rendered in [`frontend/src/components/coding/CodingAgentPanel.jsx`](file:///d:/sih/project/frontend/src/components/coding/CodingAgentPanel.jsx) with dedicated subagent badges and collapsible result cards.

---

## Pillar 3: Steering

### 1. Human-in-the-Loop (HITL)
- **Engine**: `HumanInTheLoopMiddleware` (`interrupt_on` in `create_deep_agent`)
- **Configurable Safety Modes**:
  - `safe` (Default): Pauses for human confirmation before executing terminal shell commands (`execute`) or running arbitrary Python sandbox code (`code_interpreter`).
  - `strict`: Pauses before *any* side-effect (commands, code interpreter, and file modifications `write_file`, `edit_file`).
  - `auto`: Unattended autonomous mode for rapid prototyping.
- **Interactive UI**:
  - Highlights risk level (`low`, `medium`, `high`) based on command syntax (e.g. `rm`, `del`, `sudo`, `subprocess`).
  - Provides instant "Approve & Run" and "Reject Action" controls in the chat panel with real-time graph resumption via LangGraph `Command(resume=...)`.

---

## Pillar 4: Context Management

### 1. Skills
- **Middleware**: `SkillsMiddleware` (`skills=["/.skills", "/skills"]`)
- **Workspace Seeding**:
  - Built-in domain skills located in [`backend/app/skills/`](file:///d:/sih/project/backend/app/skills/) are automatically seeded into `/.skills/` in the user's workspace:
    - `fastapi-dev`: Router architecture, dependency injection, and Pydantic schemas.
    - `git-workflow`: Branching, diffing, status inspection, and conventional commits.
    - `python-testing`: Pytest patterns, fixture isolation, and assertion debugging.
    - `react-components`: React 18 hooks, styling, and modern UI practices.
- **Usage**: The agent consults `SKILL.md` documents on-demand as cheatsheets without loading all text into the primary prompt.

### 2. Memory
- **Middleware**: `MemoryMiddleware` (`memory=["/.agents/AGENTS.md", "/AGENTS.md"]`)
- **Tool**: `update_memory(category: str, rule: str) -> str`
- **Persistence**:
  - Preserved in `/.agents/AGENTS.md` in the workspace root.
  - Loaded automatically at agent startup and injected into the prompt so project conventions persist across restarts.

### 3. Summarization
- **Middleware**: `SummarizationMiddleware`
- **Functionality**: Automatically compresses and compacts long conversation histories when message counts or token volumes exceed thresholds, preserving key decisions while shedding obsolete intermediate tool noise.

### 4. Context Offloading
- **Tool**: `offload_context(title: str, content: str) -> str`
- **Output Storage**:
  - Writes bulky text (huge logs, full API schemas, raw datasets) to `/.shield/scratch/<title>_<timestamp>.md`.
  - Replaces the bulky output in LLM context with a concise preview and file pointer, accessible via `read_file` when specific slices are required.

### 5. Prompt Caching
- **Middleware**: `PromptCachingMiddleware`
- **Functionality**: Structures system prompts, domain skills, and persistent rules with model-appropriate cache breakpoints (compatible with Anthropic Claude, Google Gemini, and OpenAI), reducing API latency and token costs by up to 80% on iterative turns.

---

## Frontend Integration & Visual Indicators

In [`frontend/src/components/coding/CodingAgentPanel.jsx`](file:///d:/sih/project/frontend/src/components/coding/CodingAgentPanel.jsx):
1. **Capabilities Quick Bar**: Four visual pills (Execution, Delegation, Steering, Context) with an interactive architecture popup (`Info` icon).
2. **Tool Execution Cards**: Color-coded badges for Python Sandbox (`#ec4899`), Subagent Delegation (`#c084fc`), Plan Tracking (`#22d3ee`), Agent Memory (`#fbbf24`), and Context Offloading (`#34d399`).
3. **One-Click Capability Prompts**: Quick action buttons to immediately exercise Planning, Sandbox Code, Subagents, and Memory.
