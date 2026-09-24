import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage

from app.config import settings
from app.core.llm import get_llm
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
) -> Dict[str, Any]:
    """
    Coding Agent generating and running Python scripts inside the isolated sandbox.
    Includes automated diagnosis and retry loop upon execution failure.
    """
    sandbox = executor or SandboxExecutor(SandboxConfig(workspace_dir=workspace_path))
    llm = get_llm(temperature=0.1)

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
                f"2. Ensure all file operations target the workspace directory.\n"
                f"3. Do not use prohibited network or system commands.\n\n"
                f"Task Requirement:\n{task_description}\n"
            )
            if attempt > 0 and last_result:
                prompt += (
                    f"\n--- PREVIOUS ATTEMPT FAILED ---\n"
                    f"Previous Code:\n```python\n{current_code}\n```\n\n"
                    f"Execution Error / Traceback:\n{last_result.stderr or last_result.error}\n"
                    f"Stdout:\n{last_result.stdout}\n\n"
                    f"INSTRUCTIONS FOR FIX:\n"
                    f"Carefully analyze the error above and output a complete, corrected Python script satisfying the task requirement without using invalid APIs or causing exceptions."
                )

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            current_code = _extract_code_from_markdown(str(response.content))

        # Execute inside isolated sandbox
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
                "code": current_code,
                "stdout": exec_result.stdout,
                "artifacts": exec_result.artifacts,
                "attempts": attempt + 1,
                "error": None,
            }

        logger.warning(f"Sandbox execution attempt {attempt + 1} failed: {exec_result.stderr}")
        current_instruction = f"Fix code error: {exec_result.stderr or exec_result.error}"

    return {
        "agent": "coding_agent",
        "success": False,
        "code": current_code,
        "stdout": last_result.stdout if last_result else "",
        "stderr": last_result.stderr if last_result else "",
        "artifacts": last_result.artifacts if last_result else [],
        "attempts": max_retries + 1,
        "error": last_result.stderr if last_result else "Execution failed",
    }
