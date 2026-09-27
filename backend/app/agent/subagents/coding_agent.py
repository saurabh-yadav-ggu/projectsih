import os
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage

from app.config import settings
from app.core.llm import get_llm
from app.sandbox.docker_executor import DockerSandboxExecutor
from app.sandbox.docker_backend import get_or_create_sandbox_backend, cleanup_session_sandbox
from app.sandbox.executor import SandboxExecutor
from app.sandbox.models import SandboxConfig, ExecutionResult

logger = logging.getLogger("app.agent.subagents.coding")


def _extract_code_from_markdown(text: str) -> str:
    cleaned = text.strip()
    match = re.search(r"```(?:python)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return cleaned


async def run_coding_agent(
    task_description: str,
    workspace_path: Path,
    context_code: str = "",
    max_retries: int = 2,
    executor: Optional[SandboxExecutor] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Autonomous Coding Agent powered by the Deep Agents harness and LocalShellBackend.
    Inspects, plans, writes, and verifies code inside the workspace.
    Falls back gracefully to isolated sandbox executor if required.
    """
    workspace_path.mkdir(parents=True, exist_ok=True)

    # 1. Primary: Run via Deep Agents harness
    try:
        from deepagents import create_deep_agent
        from langgraph.checkpoint.memory import MemorySaver
        from app.services.coding_runner import resolve_coding_model

        task_session_id = f"subagent-{int(time.time() * 1000)}"
        backend = get_or_create_sandbox_backend(workspace_dir=workspace_path, session_id=task_session_id)
        llm = resolve_coding_model(model)
        checkpointer = MemorySaver()

        clean_root = str(workspace_path).replace("\\", "/")
        system_prompt = (
            "You are an autonomous coding agent operating inside `/workspace` with access to a Docker sandbox for safe code execution.\n\n"
            "The user's message is the task/goal. Do not repeatedly ask the user for requirements, files, or confirmation.\n"
            "Your job is to autonomously: UNDERSTAND -> INSPECT -> PLAN -> IMPLEMENT -> EXECUTE -> TEST -> FIX -> RETEST -> VERIFY -> REPORT.\n\n"
            f"Active Workspace Root: '{clean_root}'. All operations take place within this workspace.\n"
            "Inspect the repository before making changes. Directly implement using filesystem tools (`write_file`, `edit_file`).\n"
            "Use the Docker sandbox to safely run tests, commands, linters, and verify results. If a test fails, diagnose the error, fix code, and retest until verified.\n"
            "Do NOT behave like a clarification chatbot. Start working immediately.\n"
            "Provide a concise final summary of what changed, modified files, and verification results."
        )

        from app.agent.coding_tools import build_coding_tools
        coding_tools = build_coding_tools(workspace_path)

        try:
            from deepagents_code.agent import create_cli_agent
            agent, comp_backend = create_cli_agent(
                model=llm,
                assistant_id=task_session_id,
                sandbox=backend,
                sandbox_type=None,
                cwd=workspace_path,
                checkpointer=checkpointer,
                tools=coding_tools,
                system_prompt=system_prompt,
                interactive=False,
                auto_approve=True,
                enable_ask_user=False,
                enable_memory=True,
                enable_skills=True,
                enable_shell=True,
            )
        except Exception as decode_err:
            logger.warning(f"Could not initialize decode agent ({decode_err}), falling back to create_deep_agent")
            from deepagents import create_deep_agent
            agent = create_deep_agent(
                model=llm,
                backend=backend,
                checkpointer=checkpointer,
                tools=coding_tools,
                system_prompt=system_prompt,
            )

        thread_id = f"coding-task-{int(time.time() * 1000)}"
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": int(os.getenv("CODING_AGENT_RECURSION_LIMIT", "250")),
        }

        prompt = task_description
        if context_code:
            prompt += f"\n\nReference Context Code:\n```python\n{context_code}\n```"

        final_response = ""
        artifacts = []

        async for event in agent.astream_events(
            {"messages": [("user", prompt)]},
            config=config,
            version="v2",
        ):
            kind = event.get("event")
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content"):
                    c = chunk.content
                    if isinstance(c, str):
                        final_response += c
                    elif isinstance(c, list):
                        for b in c:
                            if isinstance(b, str):
                                final_response += b
                            elif isinstance(b, dict) and b.get("type") == "text":
                                final_response += b.get("text", "")

            elif kind == "on_tool_end":
                tool_name = event.get("name")
                if tool_name in ("write_file", "edit_file"):
                    tool_input = event.get("data", {}).get("input", {})
                    path = ""
                    if isinstance(tool_input, dict):
                        path = tool_input.get("file_path") or tool_input.get("path") or ""
                    if path:
                        artifacts.append({"path": str(workspace_path / path), "filename": Path(path).name})

        cleanup_session_sandbox(task_session_id)
        return {
            "agent": "coding_agent",
            "success": True,
            "response": final_response or "Coding task completed successfully.",
            "artifacts": artifacts,
            "error": None,
        }

    except Exception as exc:
        logger.warning(f"Deep Agents invocation encountered exception ({exc}), falling back to SandboxExecutor")

    # 2. Fallback: DockerSandboxExecutor single-shot script retry loop
    sandbox = executor or DockerSandboxExecutor(SandboxConfig(workspace_dir=workspace_path))
    fallback_llm = get_llm(temperature=0.1)

    current_instruction = task_description
    current_code = context_code
    last_result: Optional[ExecutionResult] = None

    for attempt in range(max_retries + 1):
        if not current_code or attempt > 0:
            prompt = (
                f"You are the Shield AI Coding Agent.\n"
                f"Generate clean, robust, executable Python code to accomplish the task below.\n"
                f"RULES:\n"
                f"1. Output ONLY the Python code inside ```python ... ``` blocks.\n"
                f"2. Ensure all file operations target the workspace directory.\n\n"
                f"Task Requirement:\n{task_description}\n"
            )
            if attempt > 0 and last_result:
                prompt += (
                    f"\n--- PREVIOUS ATTEMPT FAILED ---\n"
                    f"Previous Code:\n```python\n{current_code}\n```\n\n"
                    f"Execution Error:\n{last_result.stderr or last_result.error}\n\n"
                    f"INSTRUCTIONS FOR FIX: Output a complete, corrected Python script satisfying the task requirement."
                )

            response = await fallback_llm.ainvoke([HumanMessage(content=prompt)])
            current_code = _extract_code_from_markdown(str(response.content))

        exec_result = await sandbox.execute(
            code=current_code,
            workspace=workspace_path,
            check_security=True,
        )
        last_result = exec_result

        if exec_result.success:
            return {
                "agent": "coding_agent",
                "success": True,
                "response": exec_result.stdout,
                "code": current_code,
                "stdout": exec_result.stdout,
                "artifacts": exec_result.artifacts,
                "attempts": attempt + 1,
                "error": None,
            }

        logger.warning(f"Sandbox execution attempt {attempt + 1} failed: {exec_result.stderr}")

    return {
        "agent": "coding_agent",
        "success": False,
        "response": last_result.stderr if last_result else "Execution failed",
        "code": current_code,
        "stdout": last_result.stdout if last_result else "",
        "stderr": last_result.stderr if last_result else "",
        "artifacts": last_result.artifacts if last_result else [],
        "attempts": max_retries + 1,
        "error": last_result.stderr if last_result else "Execution failed",
    }
