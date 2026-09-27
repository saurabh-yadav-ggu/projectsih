import os
import asyncio
import logging
import time
import uuid
import shutil
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Dict, List, Optional

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langgraph.checkpoint.memory import MemorySaver
from app.sandbox.docker_backend import get_or_create_sandbox_backend, cleanup_session_sandbox
from langgraph.types import Command

from app.config import settings
from app.core.llm import get_llm
from app.services.coding_workspace import CodingWorkspaceService
from app.database import SessionLocal
from app.repositories import CodingRepository

logger = logging.getLogger("app.services.coding_runner")

CODING_RECURSION_LIMIT = int(os.getenv("CODING_AGENT_RECURSION_LIMIT", "250"))


def resolve_coding_model(model_spec: Optional[str] = None):
    """Resolves chat model using existing application config with provider fallback."""
    if not model_spec or model_spec == "default":
        return get_llm(temperature=0.1)

    spec_lower = model_spec.lower()

    if spec_lower.startswith("google:") or "gemini" in spec_lower:
        raw_name = model_spec.split(":", 1)[1] if ":" in model_spec else model_spec
        if raw_name in ("gemini-flash", "gemini"):
            raw_name = "gemini-2.5-flash"
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=raw_name)

    elif spec_lower.startswith("mistral:") or spec_lower.startswith("mistralai:") or "mistral" in spec_lower or "codestral" in spec_lower:
        raw_name = model_spec.split(":", 1)[1] if ":" in model_spec else model_spec
        if settings.MISTRAL_API_KEY:
            try:
                from langchain_mistralai import ChatMistralAI
                return ChatMistralAI(
                    model=raw_name or settings.MISTRAL_MODEL,
                    api_key=settings.MISTRAL_API_KEY,
                    temperature=0.1,
                    max_tokens=4096,
                )
            except Exception as exc:
                logger.warning(f"Could not initialize ChatMistralAI ({exc}), using default LLM")
        return get_llm(temperature=0.1, model=raw_name)

    elif spec_lower.startswith("openai:") or "gpt-" in spec_lower:
        raw_name = model_spec.split(":", 1)[1] if ":" in model_spec else model_spec
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=raw_name, temperature=0.1)

    elif spec_lower.startswith("claude") or spec_lower.startswith("anthropic:"):
        raw_name = model_spec.split(":", 1)[1] if ":" in model_spec else model_spec
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model_name=raw_name, temperature=0.1)

    elif spec_lower.startswith("ollama:"):
        raw_name = model_spec.split(":", 1)[1]
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=raw_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1,
        )

    return get_llm(temperature=0.1, model=model_spec)


import shutil
import uuid
from app.agent.coding_tools import build_coding_tools


DEFAULT_CODING_SUBAGENTS = [
    {
        "name": "code-reviewer",
        "description": "Reviews code modifications for potential bugs, security vulnerabilities, edge cases, and style consistency.",
        "system_prompt": (
            "You are an expert code reviewer subagent. Analyze the given code or files. "
            "Inspect code for logic flaws, security vulnerabilities, regression risks, and styling. "
            "Provide clean, bulleted, actionable feedback."
        ),
    },
    {
        "name": "code-researcher",
        "description": "Explores the workspace codebase to discover function definitions, imports, symbols, and dependencies.",
        "system_prompt": (
            "You are a code researcher subagent. Use glob, grep, and file reading tools to investigate "
            "the codebase, trace dependencies, locate functions/classes, and summarize architecture."
        ),
    },
    {
        "name": "test-runner",
        "description": "Executes unit and integration tests and analyzes test output or failure traces.",
        "system_prompt": (
            "You are an automated testing subagent. Run tests using pytest or shell execution, "
            "diagnose failures, and report concise test outcomes."
        ),
    },
]


def _seed_workspace_assets(workspace_dir: Path):
    """
    Seeds built-in skills, persistent agent memory, and sandbox scratchpad
    into the active workspace root if not already present.
    """
    clean_workspace = workspace_dir.resolve()
    clean_workspace.mkdir(parents=True, exist_ok=True)

    # 1. Seed Skills into /.skills
    skills_dest = clean_workspace / ".skills"
    skills_dest.mkdir(parents=True, exist_ok=True)
    builtin_skills = Path(__file__).resolve().parent.parent / "skills"
    if builtin_skills.exists():
        for skill_dir in builtin_skills.iterdir():
            if skill_dir.is_dir():
                target = skills_dest / skill_dir.name
                if not target.exists():
                    try:
                        shutil.copytree(skill_dir, target)
                    except Exception as exc:
                        logger.warning(f"Could not copy skill {skill_dir.name}: {exc}")

    # 2. Seed Memory into /.agents/AGENTS.md
    agents_dir = clean_workspace / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    agents_md = agents_dir / "AGENTS.md"
    initial_memory = (
        "# Autonomous Coding Agent Protocol & Workspace Rules\n\n"
        "The user's message is the task/goal. Do not repeatedly ask the user for requirements, files, or confirmation.\n\n"
        "### Autonomous Loop:\n"
        "UNDERSTAND -> INSPECT -> PLAN -> IMPLEMENT -> EXECUTE -> TEST -> FIX -> RETEST -> VERIFY -> REPORT\n\n"
        "### Core Principles:\n"
        "- Inspect `/workspace` before making changes. Understand architecture, dependencies, and configuration.\n"
        "- Create an internal plan automatically in `/.shield/PLAN.md` using `create_plan`.\n"
        "- Implement changes directly using `write_file` and `edit_file`.\n"
        "- Use the Docker sandbox (`code_interpreter`, `verify_task`, `execute`) to run code, tests, linters, and builds.\n"
        "- If tests or commands fail, diagnose root cause, modify code, and retest until verified.\n"
        "- Do NOT behave like a clarification chatbot. Start working immediately.\n"
        "- Final response: concise summary of what changed, modified files, test execution, and verification pass.\n"
    )
    if not agents_md.exists() or len(agents_md.read_text(encoding="utf-8", errors="ignore")) < 100:
        agents_md.write_text(initial_memory, encoding="utf-8")

    # 3. Ensure .shield scratchpad and plan directories exist
    shield_dir = clean_workspace / ".shield"
    shield_dir.mkdir(parents=True, exist_ok=True)
    (shield_dir / "scratch").mkdir(parents=True, exist_ok=True)


def _get_hitl_interrupt_config(hitl_mode: str) -> Optional[Dict[str, bool]]:
    if hitl_mode == "strict":
        return {
            "execute": True,
            "code_interpreter": True,
            "write_file": True,
            "edit_file": True,
        }
    elif hitl_mode == "safe":
        return {
            "execute": True,
            "code_interpreter": True,
        }
    return None


class CodingAgentSession:
    def __init__(
        self,
        session_id: str,
        user_id: int,
        workspace_dir: Path,
        model: Optional[str] = None,
        hitl_mode: str = "safe"
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.workspace_dir = workspace_dir
        self.model = model or "default"
        self.hitl_mode = hitl_mode or "safe"
        self.checkpointer = MemorySaver()
        self.backend = get_or_create_sandbox_backend(workspace_dir=self.workspace_dir, session_id=self.session_id)
        _seed_workspace_assets(self.workspace_dir)
        self._init_graph()

    def _init_graph(self):
        resolved_model = resolve_coding_model(self.model)
        clean_root = str(self.workspace_dir).replace("\\", "/")

        system_prompt = (
            "You are an autonomous coding agent operating inside `/workspace` with access to a Docker sandbox for safe code execution.\n\n"
            "The user's message is the task/goal. Do not repeatedly ask the user for requirements, files, implementation details, or confirmation.\n\n"
            "Your job is to autonomously:\n"
            "UNDERSTAND -> INSPECT -> PLAN -> IMPLEMENT -> EXECUTE -> TEST -> FIX -> RETEST -> VERIFY -> REPORT\n\n"
            "### CORE BEHAVIOR\n"
            "1. Understand the user's requested goal.\n"
            f"2. Inspect the repository at '{clean_root}' before making changes.\n"
            "3. Identify the relevant files, architecture, dependencies, configuration, and existing implementation.\n"
            "4. Create an internal plan automatically: invoke `create_plan(title, steps, goal)` to track milestones in `/.shield/PLAN.md`.\n"
            "5. Implement the changes directly using filesystem tools (`write_file`, `edit_file`).\n"
            "6. Use the Docker sandbox (`code_interpreter`, `verify_task`, or `execute`) to safely run:\n"
            "   * application code\n"
            "   * scripts\n"
            "   * tests\n"
            "   * linters\n"
            "   * formatters\n"
            "   * type checks\n"
            "   * builds\n"
            "   * migrations\n"
            "   * integration tests\n"
            "7. Inspect command output and errors.\n"
            "8. If something fails:\n"
            "   * determine the root cause\n"
            "   * modify the code/configuration\n"
            "   * rerun the failed command\n"
            "   * continue until it works (DO NOT stop or yield back to the user on failure; remain in the loop until verified)\n"
            "9. After implementation, perform a final verification against the original goal.\n"
            "10. Only then report the result to the user.\n\n"
            "### AUTONOMOUS CODING LOOP:\n"
            "User Goal -> Inspect Repository -> Understand Architecture -> Create Internal Plan -> Implement -> Run in Docker Sandbox -> Test -> (If Failed: Diagnose Error -> Fix Code -> Retest in loop) -> Final Verification -> Report Completion\n\n"
            "### DO NOT BEHAVE LIKE A CLARIFICATION CHATBOT:\n"
            "Never start with questions such as:\n"
            "* 'What is the specific task?'\n"
            "* 'Which files should I modify?'\n"
            "* 'What requirements do you have?'\n"
            "* 'Should I use this approach?'\n"
            "* 'Would you like me to proceed?'\n"
            "* 'Can you provide more context?'\n"
            "If the user's request is reasonably clear, START WORKING IMMEDIATELY.\n\n"
            "### USE THE DOCKER SANDBOX INTELLIGENTLY:\n"
            "Use the sandbox as the primary execution environment for untrusted or potentially destructive code.\n"
            "Prefer: inspect -> modify -> execute in sandbox -> observe -> fix -> execute again.\n"
            "Do not assume code works merely because it looks correct. Actually execute and verify it whenever possible.\n\n"
            "### WHEN YOU MAY ASK THE USER:\n"
            "Ask the user ONLY when you are genuinely blocked, for example:\n"
            "* required credentials/API keys are unavailable\n"
            "* the task contains two fundamentally incompatible interpretations\n"
            "* an irreversible production action requires explicit approval\n"
            "* an external resource is unavailable and cannot be inferred\n"
            "* the requested behavior contradicts an explicit project requirement\n"
            "Even then, ask ONE focused question, not a questionnaire.\n\n"
            "### FINAL RESPONSE FORMAT:\n"
            "After completing the task, provide only a concise summary:\n"
            "* What changed\n"
            "* Important files/components modified\n"
            "* Tests/checks executed\n"
            "* Whether everything passed\n"
            "* Any remaining issue that genuinely requires the user\n"
            "Do not describe hypothetical work that was not actually performed.\n\n"
            "### THINKING PROCESS:\n"
            "Enclose all internal thinking, inspection analysis, reasoning, and plan breakdown inside `<thought>...</thought>` tags.\n"
            f"Active Workspace Root: '{clean_root}'. The sandbox working directory is `/workspace` (or '.')."
        )

        interrupt_on = _get_hitl_interrupt_config(self.hitl_mode)
        custom_tools = build_coding_tools(self.workspace_dir)

        # Initialize decode (deepagents_code) CLI agent connected to Docker sandbox
        try:
            from deepagents_code.agent import create_cli_agent
            logger.info("Initializing CodingAgentSession with decode (deepagents_code) agent engine")
            graph, comp_backend = create_cli_agent(
                model=resolved_model,
                assistant_id=f"shield-coding-{self.session_id}",
                sandbox=self.backend,
                sandbox_type=None,
                cwd=self.workspace_dir,
                checkpointer=self.checkpointer,
                tools=custom_tools,
                system_prompt=system_prompt,
                interactive=True,
                auto_approve=(self.hitl_mode in ("open", "auto")),
                enable_ask_user=False,
                enable_memory=True,
                enable_skills=True,
                enable_shell=True,
            )
            self.graph = graph
            self.composite_backend = comp_backend
        except Exception as err:
            logger.warning(f"Could not initialize decode agent ({err}), falling back to create_deep_agent")
            self.graph = create_deep_agent(
                model=resolved_model,
                backend=self.backend,
                checkpointer=self.checkpointer,
                system_prompt=system_prompt,
                tools=custom_tools,
                subagents=DEFAULT_CODING_SUBAGENTS,
                skills=["/.skills", "/skills"],
                memory=["/.agents/AGENTS.md", "/AGENTS.md"],
                interrupt_on=interrupt_on,
            )

    def set_hitl_mode(self, hitl_mode: str):
        if self.hitl_mode != hitl_mode:
            self.hitl_mode = hitl_mode
            self._init_graph()


# Active in-memory session cache
_coding_sessions: Dict[str, CodingAgentSession] = {}


def reset_coding_session(session_id: str):
    cleanup_session_sandbox(session_id)
    if session_id in _coding_sessions:
        del _coding_sessions[session_id]


def get_or_create_coding_session(
    session_id: str,
    user_id: int,
    workspace_path: Optional[str] = None,
    model: Optional[str] = None,
    hitl_mode: Optional[str] = None,
) -> CodingAgentSession:
    ws = CodingWorkspaceService.resolve_workspace_dir(user_id, workspace_path)

    existing = _coding_sessions.get(session_id)
    if existing and existing.workspace_dir == ws and (model is None or existing.model == model):
        if hitl_mode and existing.hitl_mode != hitl_mode:
            existing.set_hitl_mode(hitl_mode)
        return existing

    session = CodingAgentSession(
        session_id,
        user_id=user_id,
        workspace_dir=ws,
        model=model,
        hitl_mode=hitl_mode or "safe"
    )
    _coding_sessions[session_id] = session
    return session


def _extract_approval_info(interrupt_obj: Any) -> Dict[str, Any]:
    val = getattr(interrupt_obj, "value", {})
    action_requests = val.get("action_requests", []) if isinstance(val, dict) else []
    req = action_requests[0] if action_requests else {}
    action_name = req.get("name", "execute")
    args = req.get("args", {})

    cmd_str = args.get("command") or args.get("path") or args.get("file_path") or ""
    if not cmd_str and action_name in ("code_interpreter", "verify_task"):
        code = args.get("code") or args.get("test_code", "")
        code_lines = code.splitlines()
        preview = "\n".join(code_lines[:4])
        if len(code_lines) > 4:
            preview += f"\n... (+{len(code_lines) - 4} lines)"
        cmd_str = preview or "(empty code)"
    elif not cmd_str:
        cmd_str = str(args)

    risk_level = "low"
    if action_name == "execute":
        dangerous_words = ("rm ", "del ", "rmdir", "drop ", "kill ", "format ", "mkfs", "sudo ")
        if any(w in cmd_str.lower() for w in dangerous_words):
            risk_level = "high"
        else:
            risk_level = "medium"
    elif action_name in ("code_interpreter", "verify_task"):
        code_str = (args.get("code") or args.get("test_code", "")).lower()
        dangerous_code = ("os.system", "subprocess", "shutil.rmtree", "socket", "__import__", "eval(")
        if any(w in code_str for w in dangerous_code):
            risk_level = "high"
        else:
            risk_level = "low" if action_name == "verify_task" else "medium"
    elif action_name in ("write_file", "edit_file"):
        risk_level = "medium"

    action_desc = req.get("description")
    if not action_desc:
        if action_name == "code_interpreter":
            action_desc = "Approval required to execute Python code in Sandbox"
        elif action_name == "verify_task":
            action_desc = f"Approval required to run sandbox verification for '{args.get('goal_or_step', 'milestone')}'"
        elif action_name == "execute":
            action_desc = "Approval required to run command in terminal"
        else:
            action_desc = f"Approval required to perform '{action_name}'"

    return {
        "action": action_name,
        "command": cmd_str,
        "args": args,
        "risk_level": risk_level,
        "description": action_desc,
    }


async def run_coding_agent_stream(
    session_id: str,
    user_id: int,
    user_prompt: str,
    workspace_path: Optional[str] = None,
    model: Optional[str] = None,
    hitl_mode: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Runs the deep coding agent and yields structured protocol events."""
    session = get_or_create_coding_session(
        session_id,
        user_id,
        workspace_path=workspace_path,
        model=model,
        hitl_mode=hitl_mode
    )

    # 1. Persist user prompt to SQLite thread database
    try:
        with SessionLocal() as db:
            CodingRepository.save_message(db, session_id, user_id, role="user", content=user_prompt)
    except Exception as save_err:
        logger.warning(f"Could not persist user message to DB for session {session_id}: {save_err}")

    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": CODING_RECURSION_LIMIT,
    }

    # 2. Check if checkpointer has history or if we need to retrieve conversation from DB
    state = session.graph.get_state(config)
    existing_graph_messages = state.values.get("messages", []) if state and hasattr(state, "values") else []

    if not existing_graph_messages:
        try:
            with SessionLocal() as db:
                db_messages = CodingRepository.get_messages(db, session_id, user_id)
            if db_messages and len(db_messages) > 1:
                # Retrieve entire conversation history from database so model resumes thread seamlessly
                messages_input = [(m["role"], m["content"]) for m in db_messages]
            else:
                messages_input = [("user", user_prompt)]
        except Exception as fetch_err:
            logger.warning(f"Could not load conversation history from DB for session {session_id}: {fetch_err}")
            messages_input = [("user", user_prompt)]
    else:
        # Checkpointer already retains thread history
        messages_input = [("user", user_prompt)]

    yield {
        "type": "agent_status",
        "status": "thinking",
        "session_id": session_id,
    }

    tool_start_times: Dict[str, float] = {}
    accumulated_chunks: List[str] = []

    def _persist_assistant_reply():
        if accumulated_chunks:
            full_text = "".join(accumulated_chunks).strip()
            if full_text:
                try:
                    with SessionLocal() as db:
                        CodingRepository.save_message(db, session_id, user_id, role="assistant", content=full_text)
                except Exception as save_err:
                    logger.warning(f"Could not persist assistant message to DB for session {session_id}: {save_err}")

    try:
        async for event in session.graph.astream_events(
            {"messages": messages_input},
            config=config,
            version="v2",
        ):
            kind = event.get("event")
            run_id = event.get("run_id", "")

            # 1. Chat model streaming chunks
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content"):
                    content = chunk.content
                    if isinstance(content, str) and content:
                        accumulated_chunks.append(content)
                        yield {
                            "type": "agent_chunk",
                            "session_id": session_id,
                            "content": content,
                        }
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, str):
                                accumulated_chunks.append(block)
                                yield {"type": "agent_chunk", "session_id": session_id, "content": block}
                            elif isinstance(block, dict) and block.get("type") == "text":
                                block_text = block.get("text", "")
                                accumulated_chunks.append(block_text)
                                yield {"type": "agent_chunk", "session_id": session_id, "content": block_text}

            # 2. Tool execution started
            elif kind == "on_tool_start":
                tool_name = event.get("name", "tool")
                tool_inputs = event.get("data", {}).get("input", {})
                tool_start_times[run_id] = time.time()

                yield {
                    "type": "tool_started",
                    "session_id": session_id,
                    "tool_id": run_id,
                    "tool": tool_name,
                    "args": tool_inputs,
                }

                if tool_name == "task":
                    subagent_name = tool_inputs.get("name") or tool_inputs.get("subagent") or "subagent"
                    yield {
                        "type": "subagent_started",
                        "session_id": session_id,
                        "subagent": subagent_name,
                        "description": tool_inputs.get("description", ""),
                    }

                yield {
                    "type": "agent_status",
                    "status": "executing_tool",
                    "tool": tool_name,
                }

            # 3. Tool execution finished
            elif kind == "on_tool_end":
                tool_name = event.get("name", "tool")
                raw_output = event.get("data", {}).get("output", "")
                output_str = str(raw_output)
                start_t = tool_start_times.pop(run_id, time.time())
                duration_ms = int((time.time() - start_t) * 1000)

                yield {
                    "type": "tool_finished",
                    "session_id": session_id,
                    "tool_id": run_id,
                    "tool": tool_name,
                    "duration_ms": duration_ms,
                    "output": output_str[:4000],
                }

                if tool_name == "task":
                    yield {
                        "type": "subagent_finished",
                        "session_id": session_id,
                        "output": output_str[:2000],
                    }

                # File modified notifications across filesystem, plan, memory, and offloaded scratch
                if tool_name in ("write_file", "edit_file"):
                    tool_input = event.get("data", {}).get("input", {})
                    path = ""
                    if isinstance(tool_input, dict):
                        path = tool_input.get("file_path") or tool_input.get("path") or ""
                    yield {
                        "type": "file_changed",
                        "path": path,
                        "change_type": "modified",
                    }
                elif tool_name in ("create_plan", "update_plan", "verify_task"):
                    yield {
                        "type": "file_changed",
                        "path": ".shield/PLAN.md",
                        "change_type": "modified",
                    }
                elif tool_name == "update_memory":
                    yield {
                        "type": "file_changed",
                        "path": ".agents/AGENTS.md",
                        "change_type": "modified",
                    }
                elif tool_name == "offload_context":
                    yield {
                        "type": "file_changed",
                        "path": ".shield/scratch",
                        "change_type": "modified",
                    }
                elif tool_name in ("execute", "code_interpreter"):
                    yield {
                        "type": "file_changed",
                        "path": "",
                        "change_type": "modified",
                    }

        # 4. Check for Human-in-the-Loop Interrupts
        state = session.graph.get_state(config)
        if state.interrupts:
            _persist_assistant_reply()
            req_info = _extract_approval_info(state.interrupts[0])
            request_id = str(uuid.uuid4())

            yield {
                "type": "agent_approval_required",
                "session_id": session_id,
                "request_id": request_id,
                "action": req_info["action"],
                "command": req_info["command"],
                "args": req_info["args"],
                "risk_level": req_info["risk_level"],
                "description": req_info["description"],
                "allowed_decisions": ["approve", "reject"],
            }
            yield {
                "type": "agent_status",
                "status": "waiting_approval",
                "session_id": session_id,
            }
            return

        # 5. Persist assistant final response to SQLite database
        _persist_assistant_reply()

        yield {
            "type": "agent_status",
            "status": "idle",
            "session_id": session_id,
        }
        yield {
            "type": "agent_completed",
            "session_id": session_id,
        }

    except Exception as exc:
        _persist_assistant_reply()
        logger.exception("Error in coding agent execution stream")
        yield {
            "type": "agent_chunk",
            "session_id": session_id,
            "content": f"\n\n⚠️ **Agent Error:** {exc}",
        }
        yield {
            "type": "error",
            "session_id": session_id,
            "message": str(exc),
        }
        yield {
            "type": "agent_status",
            "status": "error",
            "session_id": session_id,
        }
        yield {
            "type": "agent_completed",
            "session_id": session_id,
        }


async def resume_coding_agent_approval(
    session_id: str,
    user_id: int,
    decision: str,
    request_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Resumes an interrupted agent run following a Human-in-the-Loop approval decision."""
    session = get_or_create_coding_session(session_id, user_id)
    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": CODING_RECURSION_LIMIT,
    }

    # Record the decision note in database thread
    try:
        with SessionLocal() as db:
            decision_text = f"🛡️ **User Approved Action**" if decision == "approve" else "🛑 **User Rejected Action**"
            CodingRepository.save_message(db, session_id, user_id, role="assistant", content=decision_text)
    except Exception as save_err:
        logger.warning(f"Could not record decision message to DB for session {session_id}: {save_err}")

    dec_type = "approve" if decision == "approve" else "reject"
    command = Command(resume={"decisions": [{"type": dec_type}]})

    yield {
        "type": "agent_status",
        "status": "thinking",
        "session_id": session_id,
    }

    tool_start_times: Dict[str, float] = {}
    accumulated_resume_chunks: List[str] = []

    def _persist_resume_reply():
        if accumulated_resume_chunks:
            full_text = "".join(accumulated_resume_chunks).strip()
            if full_text:
                try:
                    with SessionLocal() as db:
                        CodingRepository.save_message(db, session_id, user_id, role="assistant", content=full_text)
                except Exception as save_err:
                    logger.warning(f"Could not persist assistant resume message to DB for session {session_id}: {save_err}")

    try:
        async for event in session.graph.astream_events(
            command,
            config=config,
            version="v2",
        ):
            kind = event.get("event")
            run_id = event.get("run_id", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content"):
                    content = chunk.content
                    if isinstance(content, str) and content:
                        accumulated_resume_chunks.append(content)
                        yield {"type": "agent_chunk", "session_id": session_id, "content": content}
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, str):
                                accumulated_resume_chunks.append(block)
                                yield {"type": "agent_chunk", "session_id": session_id, "content": block}
                            elif isinstance(block, dict) and block.get("type") == "text":
                                block_text = block.get("text", "")
                                accumulated_resume_chunks.append(block_text)
                                yield {"type": "agent_chunk", "session_id": session_id, "content": block_text}

            elif kind == "on_tool_start":
                tool_name = event.get("name", "tool")
                tool_inputs = event.get("data", {}).get("input", {})
                tool_start_times[run_id] = time.time()
                yield {
                    "type": "tool_started",
                    "session_id": session_id,
                    "tool_id": run_id,
                    "tool": tool_name,
                    "args": tool_inputs,
                }

                if tool_name == "task":
                    subagent_name = tool_inputs.get("name") or tool_inputs.get("subagent") or "subagent"
                    yield {
                        "type": "subagent_started",
                        "session_id": session_id,
                        "subagent": subagent_name,
                        "description": tool_inputs.get("description", ""),
                    }

                yield {
                    "type": "agent_status",
                    "status": "executing_tool",
                    "tool": tool_name,
                }

            elif kind == "on_tool_end":
                tool_name = event.get("name", "tool")
                raw_output = event.get("data", {}).get("output", "")
                output_str = str(raw_output)
                start_t = tool_start_times.pop(run_id, time.time())
                duration_ms = int((time.time() - start_t) * 1000)

                yield {
                    "type": "tool_finished",
                    "session_id": session_id,
                    "tool_id": run_id,
                    "tool": tool_name,
                    "duration_ms": duration_ms,
                    "output": output_str[:4000],
                }

                if tool_name == "task":
                    yield {
                        "type": "subagent_finished",
                        "session_id": session_id,
                        "output": output_str[:2000],
                    }

                if tool_name in ("write_file", "edit_file"):
                    tool_input = event.get("data", {}).get("input", {})
                    path = ""
                    if isinstance(tool_input, dict):
                        path = tool_input.get("file_path") or tool_input.get("path") or ""
                    yield {"type": "file_changed", "path": path, "change_type": "modified"}
                elif tool_name in ("create_plan", "update_plan", "verify_task"):
                    yield {"type": "file_changed", "path": ".shield/PLAN.md", "change_type": "modified"}
                elif tool_name == "update_memory":
                    yield {"type": "file_changed", "path": ".agents/AGENTS.md", "change_type": "modified"}
                elif tool_name == "offload_context":
                    yield {"type": "file_changed", "path": ".shield/scratch", "change_type": "modified"}
                elif tool_name in ("execute", "code_interpreter"):
                    yield {"type": "file_changed", "path": "", "change_type": "modified"}

        # Check for another interrupt in sequence
        state = session.graph.get_state(config)
        if state.interrupts:
            _persist_resume_reply()
            req_info = _extract_approval_info(state.interrupts[0])
            new_request_id = str(uuid.uuid4())

            yield {
                "type": "agent_approval_required",
                "session_id": session_id,
                "request_id": new_request_id,
                "action": req_info["action"],
                "command": req_info["command"],
                "args": req_info["args"],
                "risk_level": req_info["risk_level"],
                "description": req_info["description"],
                "allowed_decisions": ["approve", "reject"],
            }
            yield {
                "type": "agent_status",
                "status": "waiting_approval",
                "session_id": session_id,
            }
            return

        # Persist resume final response
        _persist_resume_reply()

        yield {
            "type": "agent_status",
            "status": "idle",
            "session_id": session_id,
        }
        yield {
            "type": "agent_completed",
            "session_id": session_id,
        }

    except Exception as exc:
        _persist_resume_reply()
        logger.exception("Error resuming coding agent approval")
        yield {"type": "agent_chunk", "session_id": session_id, "content": f"\n\n⚠️ **Agent Error:** {exc}"}
        yield {"type": "error", "session_id": session_id, "message": str(exc)}
        yield {"type": "agent_status", "status": "error", "session_id": session_id}
        yield {"type": "agent_completed", "session_id": session_id}
