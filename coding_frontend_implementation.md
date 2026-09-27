# Deep Agents Coding Studio - Frontend & HITL Integration Report

## 1. Overview & Architecture
The frontend for **Shield AI Autonomous Coding Studio** has been fully implemented and integrated directly into the existing React application, adhering to the core directive:
> *"DO NOT CREATE A SECOND APPLICATION. Integrate, don't duplicate."*

The Coding Studio operates as a rich, full-featured workspace mode inside Shield AI, sharing:
- Authentication & JWT session persistence.
- User profile & preferences.
- Theme tokens (`#000000`, `#050507`, `#111216`, `#1d4ed8`, `#22c55e`).
- Real-time WebSocket connection to `/ws/coding` and `/api/coding/ws`.

---

## 2. Integrated Components Summary

| Component | Path | Responsibility |
|---|---|---|
| **Coding API Client** | [`frontend/src/api/coding.js`](file:///d:/sih/project/frontend/src/api/coding.js) | Full REST client for sessions, file tree, read/write/delete/rename, git status, terminal execution, and approvals. |
| **WebSocket Gateway** | [`frontend/src/services/codingSocket.js`](file:///d:/sih/project/frontend/src/services/codingSocket.js) | Real-time dual-duplex transport handling agent tokens, tool execution updates, terminal stdout/stderr, and human-in-the-loop approvals. |
| **Workspace Hook** | [`frontend/src/hooks/useCodingState.js`](file:///d:/sih/project/frontend/src/hooks/useCodingState.js) | Central reactive state manager coordinating open tabs, active file, Monaco editor state, dirty file tracking, terminal streams, and agent chat messages. |
| **Workspace Container** | [`frontend/src/components/coding/CodingWorkspace.jsx`](file:///d:/sih/project/frontend/src/components/coding/CodingWorkspace.jsx) | Root container orchestrating the 3-column layout (Explorer, Monaco + Terminal Drawer, Coding Agent Panel). |
| **IDE Header** | [`frontend/src/components/coding/CodingHeader.jsx`](file:///d:/sih/project/frontend/src/components/coding/CodingHeader.jsx) | Top bar featuring mode switcher pill (`[ 💬 Chat ] [ <> Coding ]`), workspace indicator, HITL Mode Dropdown (`Safe`, `Strict`, `Full Auto`), model selector dropdown, and live status badge. |
| **File Explorer** | [`frontend/src/components/coding/FileExplorer.jsx`](file:///d:/sih/project/frontend/src/components/coding/FileExplorer.jsx) | Recursive file tree viewer with syntax-aware icons, folder expand/collapse, active file indicator, new file creation modal, file deletion, and tree reload. |
| **Monaco Editor Area** | [`frontend/src/components/coding/MonacoEditorArea.jsx`](file:///d:/sih/project/frontend/src/components/coding/MonacoEditorArea.jsx) | Full-featured Monaco code editor with multi-tab management, dirty indicators, hotkeys (`Ctrl+S` / `Cmd+S` auto-save), and syntax highlighting. |
| **Terminal Drawer** | [`frontend/src/components/coding/TerminalDrawer.jsx`](file:///d:/sih/project/frontend/src/components/coding/TerminalDrawer.jsx) | Interactive drawer supporting raw shell command execution, command history (`Up`/`Down` arrows), clear buffer, expand/collapse, and integrated Git Status / Diff viewer. |
| **Coding Agent Panel** | [`frontend/src/components/coding/CodingAgentPanel.jsx`](file:///d:/sih/project/frontend/src/components/coding/CodingAgentPanel.jsx) | Autonomous coding copilot panel with markdown streaming, expandable tool call cards (arguments, duration, output), and Human-in-the-Loop approval cards. |
| **App Routing & Shell** | [`frontend/src/App.jsx`](file:///d:/sih/project/frontend/src/App.jsx) | Seamless mode switching between Chat Assistant and Coding Studio without page reloads or auth teardown. |
| **Sidebar Integration** | [`frontend/src/components/layout/Sidebar.jsx`](file:///d:/sih/project/frontend/src/components/layout/Sidebar.jsx) | Added `Chat Assistant` and `Coding Studio` (with `IDE` badge) navigation items. |
| **TopBar Integration** | [`frontend/src/components/layout/TopBar.jsx`](file:///d:/sih/project/frontend/src/components/layout/TopBar.jsx) | Interactive toggle pill (`Chat • Coding`) allowing instantaneous workspace switching. |

---

## 3. Human-in-the-Loop (HITL) Architecture

### 3.1 Three Configurable HITL Security Modes
Users can switch HITL mode dynamically via the dropdown in the IDE Header:
1. 🛡️ **HITL: Safe (Default)**:
   - File reads, writes, and searches execute automatically.
   - All shell terminal commands (`execute`) require human operator approval.
2. 🔒 **HITL: Strict**:
   - Every potentially mutating action (`execute`, `write_file`, `edit_file`) halts and requests explicit confirmation.
3. ⚡ **Full Auto**:
   - Fully unattended execution with zero interruptions.

### 3.2 LangGraph Interruption & Resumption Engine
- **Interruption Detection**: The backend configures `create_deep_agent(interrupt_on=...)` via `HumanInTheLoopMiddleware`. When an interrupted tool is called, LangGraph pauses at the checkpoint.
- **Payload Extraction**: State inspects `state.interrupts[0].value`, extracting action name, argument details, risk assessment (`high`, `medium`, `low`), and emits `agent_approval_required` over the WebSocket.
- **Database Persistence**: The pending approval is recorded in SQLite table `coding_approvals` with user ID, session ID, command, and timestamp.
- **Resumption**: When the operator clicks **[ Approve & Run ]** or **[ Reject Action ]**, the client sends `approval_response`. The backend resumes via:
  ```python
  command = Command(resume={"decisions": [{"type": "approve" if decision == "approve" else "reject"}]})
  ```
  And streams subsequent tokens, outputs, and any chained actions back to the frontend.

### 3.3 Interactive UI Approval Card
When an approval is required, an animated card appears in the Coding Agent Panel:
- **Risk Badge**: High risk (Red) or Medium risk (Amber) based on command contents (e.g. destructive commands `rm`, `delete`, `drop`, `kill`, `sudo`).
- **Terminal Preview**: Formatted code block `$ <command>` showing the exact command or file to be modified.
- **Operator Buttons**:
  - `[ ✓ Approve & Run ]`: Green button granting immediate permission.
  - `[ ✕ Reject Action ]`: Red outline button rejecting the call, letting the agent adjust its plan without executing.
- **Audit Logging in Chat**: Appends clear status badges in the conversation history documenting whether the user approved or rejected the action.
- **Composer Lock**: Disables the input text field with a placeholder indicating execution is paused awaiting the human operator.

---

## 4. Verification & Testing
- **Production Frontend Build**: `npm run build` compiled 2122 modules cleanly in `414ms` with zero errors.
- **Backend Lint & Compilation**: Verified with `py_compile app/services/coding_runner.py` and `py_compile app/routers/coding.py` (exit code `0`).
- **Live Integration Tests**: Ran automated test scripts verifying:
  1. Interrupt trigger on `execute`.
  2. Resumption with `approve` resulting in executed command and streamed response.
  3. Resumption with `reject` resulting in graceful fallback explanation without executing the command.
- **Git Branch**: All changes are committed and staged on `coding-agent-implementation`.
