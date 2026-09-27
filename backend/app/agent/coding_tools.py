import asyncio
import logging
import time
from pathlib import Path
from typing import List, Optional
from langchain_core.tools import tool

from app.sandbox.docker_executor import DockerSandboxExecutor
from app.sandbox.models import SandboxConfig

logger = logging.getLogger("app.agent.coding_tools")


def build_coding_tools(workspace_dir: Path) -> list:
    """
    Factory creating first-class coding assistant tools bound to the active workspace.
    Includes:
    - Code Interpreter (Execution Environment)
    - Planning (Delegation)
    - Memory Management (Context Management)
    - Context Offloading (Context Management)
    """
    clean_workspace = workspace_dir.resolve()
    clean_workspace.mkdir(parents=True, exist_ok=True)
    shield_dir = clean_workspace / ".shield"
    shield_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir = shield_dir / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    agents_dir = clean_workspace / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    def _run_sandbox_sync(code: str, timeout: int = 60):
        executor = DockerSandboxExecutor(
            config=SandboxConfig(
                workspace_dir=clean_workspace,
                timeout_seconds=timeout,
            )
        )
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                def _run():
                    return asyncio.run(executor.execute(code=code, workspace=clean_workspace, check_security=True))
                return pool.submit(_run).result()
        else:
            return loop.run_until_complete(
                executor.execute(code=code, workspace=clean_workspace, check_security=True)
            )

    @tool
    def code_interpreter(code: str) -> str:
        """
        Executes Python code in an isolated sandbox within the active workspace.
        Captures stdout, stderr, execution time, and any generated file artifacts.
        Use this to evaluate logic, test snippets, analyze datasets, or verify algorithms.
        """
        try:
            res = _run_sandbox_sync(code, timeout=60)

            output_lines = []
            if res.stdout:
                output_lines.append(f"STDOUT:\n{res.stdout}")
            if res.stderr:
                output_lines.append(f"STDERR:\n{res.stderr}")
            if res.error:
                output_lines.append(f"EXECUTION ERROR: {res.error}")

            full_output = "\n".join(output_lines) or "(Code executed successfully with no output)"
            duration_info = f"[Execution time: {res.execution_time_ms:.1f}ms | Exit code: {res.exit_code}]"

            # Context Offloading: If output exceeds 200 lines or 8000 characters, offload to scratch file
            lines = full_output.splitlines()
            if len(lines) > 200 or len(full_output) > 8000:
                ts = int(time.time() * 1000)
                offload_file = scratch_dir / f"interpreter_output_{ts}.log"
                offload_file.write_text(full_output, encoding="utf-8")
                preview = "\n".join(lines[:40])
                rel_path = str(offload_file.relative_to(clean_workspace)).replace("\\", "/")
                return (
                    f"{duration_info}\n"
                    f"⚠️ Output was large ({len(lines)} lines, {len(full_output)} chars) and offloaded to context scratchpad: `/{rel_path}`\n\n"
                    f"PREVIEW (First 40 lines):\n{preview}\n...\n"
                    f"(Full output saved in `/{rel_path}` - use `read_file` if specific slices are needed)"
                )

            return f"{duration_info}\n{full_output}"

        except Exception as exc:
            logger.exception(f"Code interpreter failure: {exc}")
            return f"Code execution failed: {str(exc)}"

    @tool
    def verify_task(goal_or_step: str, test_code: str, expected_outcome: Optional[str] = None) -> str:
        """
        Executes a verification test in the isolated Sandbox to rigorously validate whether
        a specific task, milestone, or goal has been correctly implemented.
        - `goal_or_step`: Description of the goal or milestone being validated (e.g. 'Step 2: Fibonacci memoization')
        - `test_code`: Python test code with assertions to run in the sandbox
        - `expected_outcome`: Optional expected keyword, value, or condition in the test output

        Returns:
        - '✅ [VERIFIED PASS]' if all assertions succeed, exit code is 0, and expected outcome matches.
        - '❌ [VERIFIED FAIL]' with tracebacks and errors if tests fail.
        AUTONOMOUS LOOP REQUIREMENT: When FAIL is returned, you MUST stay in the autonomous loop:
        inspect the error, edit the code, and re-run verify_task until VERIFIED PASS is achieved.
        """
        try:
            res = _run_sandbox_sync(test_code, timeout=60)

            output_lines = []
            if res.stdout:
                output_lines.append(f"STDOUT:\n{res.stdout.strip()}")
            if res.stderr:
                output_lines.append(f"STDERR:\n{res.stderr.strip()}")
            if res.error:
                output_lines.append(f"EXECUTION ERROR: {res.error}")

            full_output = "\n".join(output_lines)

            # Determine pass/fail
            passed = (res.exit_code == 0) and not res.error
            if passed and expected_outcome:
                combined_text = (res.stdout + " " + res.stderr).lower()
                if expected_outcome.lower() not in combined_text:
                    passed = False
                    full_output += f"\nEXPECTED OUTCOME MISMATCH: Expected '{expected_outcome}' in output, but was not found."

            if passed:
                return (
                    f"✅ [VERIFIED PASS] Goal/Milestone '{goal_or_step}' is VERIFIED in Sandbox!\n"
                    f"[Sandbox Duration: {res.execution_time_ms:.1f}ms | Exit code: 0]\n"
                    f"{full_output or '(All test assertions passed successfully)'}\n\n"
                    f"NEXT ACTION: Call `update_plan` to mark milestone completed, and proceed to the next milestone."
                )
            else:
                return (
                    f"❌ [VERIFIED FAIL] Goal/Milestone '{goal_or_step}' verification FAILED in Sandbox!\n"
                    f"[Sandbox Duration: {res.execution_time_ms:.1f}ms | Exit code: {res.exit_code}]\n"
                    f"{full_output}\n\n"
                    f"AUTONOMOUS LOOP DIRECTIVE: The milestone is NOT verified yet. Inspect the failure above, "
                    f"modify the implementation files, and call verify_task again in the loop until VERIFIED PASS."
                )
        except Exception as exc:
            logger.exception(f"Verification execution failure: {exc}")
            return f"❌ [VERIFIED FAIL] Verification error: {str(exc)}"

    @tool
    def create_plan(title: str, steps: List[str], goal: Optional[str] = None) -> str:
        """
        Creates a structured, goal-oriented implementation plan with verification milestones.
        Saves the goal and checklist to `.shield/PLAN.md` in the workspace.
        Mandatory first step when starting any non-trivial coding task or feature.
        - `title`: Short descriptive title of the overall initiative
        - `steps`: List of sequential milestones, each with clear implementation and verification targets
        - `goal`: Optional explicit description of the final end-state goal to be achieved
        """
        try:
            plan_file = shield_dir / "PLAN.md"
            primary_goal = goal or title
            lines = [
                f"# Implementation Plan: {title}",
                f"**Primary Goal:** {primary_goal}",
                f"*Created: {time.strftime('%Y-%m-%d %H:%M:%S')}*",
                f"*Status:* In Progress (Autonomous Loop Active)",
                "",
                "## Milestones & Verification Criteria",
            ]
            for idx, step in enumerate(steps, start=1):
                lines.append(f"- [ ] **Step {idx}:** {step}")

            lines.append("")
            lines.append("## Autonomous Execution & Verification Log")
            lines.append("- [Loop Started] Plan formulated. Ready for step 1 execution.")

            plan_file.write_text("\n".join(lines), encoding="utf-8")
            return (
                f"Plan and goal successfully established in `/.shield/PLAN.md` with {len(steps)} milestones.\n"
                f"Primary Goal: '{primary_goal}'\n"
                f"NOW BEGIN THE LOOP: Update Step 1 to in_progress, implement the files, run in sandbox, and verify with verify_task."
            )
        except Exception as exc:
            return f"Could not create plan: {str(exc)}"

    @tool
    def update_plan(step_index: int, status: str, verification_result: str = "", notes: str = "") -> str:
        """
        Updates milestone progress and verification results in `.shield/PLAN.md`.
        - `step_index`: 1-based index of the milestone
        - `status`: 'completed' / 'verified', 'in_progress', or 'failed' (needs loop iteration)
        - `verification_result`: Optional summary of sandbox verification outcome (e.g. 'All assertions passed')
        - `notes`: Optional progress or architectural notes
        """
        try:
            plan_file = shield_dir / "PLAN.md"
            if not plan_file.exists():
                return "No existing plan found at `/.shield/PLAN.md`. Use `create_plan` first."

            content = plan_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            updated = False

            st_lower = status.lower()
            if st_lower in ("completed", "verified", "passed", "done"):
                marker = "- [x]"
            elif st_lower in ("in_progress", "active", "running"):
                marker = "- [/]"
            elif st_lower in ("failed", "retry", "iterating"):
                marker = "- [!]"
            else:
                marker = "- [ ]"

            for i, line in enumerate(lines):
                if line.strip().startswith("- [") and f"**Step {step_index}:**" in line:
                    prefix_end = line.find(f"**Step {step_index}:**")
                    step_text = line[prefix_end:]
                    lines[i] = f"{marker} {step_text}"
                    updated = True
                    break

            log_entry = f"- *Step {step_index} [{status}]:*"
            if verification_result.strip():
                log_entry += f" Verification: {verification_result.strip()}"
            if notes.strip():
                log_entry += f" | Notes: {notes.strip()}"

            lines.append(log_entry)

            if updated:
                plan_file.write_text("\n".join(lines), encoding="utf-8")
                return f"Updated Step {step_index} to [{status}] in `/.shield/PLAN.md`."
            else:
                return f"Step {step_index} not found in `/.shield/PLAN.md`."
        except Exception as exc:
            return f"Could not update plan: {str(exc)}"

    @tool
    def update_memory(category: str, rule: str) -> str:
        """
        Records persistent project guidelines, architectural conventions, or user preferences
        into `.agents/AGENTS.md` so that the agent retains this memory across sessions.
        - `category`: e.g. 'Coding Style', 'Architecture', 'Testing', 'Libraries'
        - `rule`: The specific preference or convention to remember
        """
        try:
            memory_file = agents_dir / "AGENTS.md"
            header = "# Project Guidelines & Agent Memory\n\nPersistent context across coding sessions.\n\n"
            current_text = memory_file.read_text(encoding="utf-8") if memory_file.exists() else header

            entry = f"\n### {category.capitalize()}\n- {rule.strip()}\n"
            if entry not in current_text:
                memory_file.write_text(current_text + entry, encoding="utf-8")
                return f"Saved memory rule under '{category}' to `/.agents/AGENTS.md`."
            return f"Rule already present in `/.agents/AGENTS.md`."
        except Exception as exc:
            return f"Could not update memory: {str(exc)}"

    @tool
    def offload_context(title: str, content: str) -> str:
        """
        Offloads large content (long logs, analysis, raw documentation) to a scratchpad file
        in `.shield/scratch/` to prevent filling the LLM context window.
        Returns the relative file path to reference in conversation.
        """
        try:
            clean_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title.lower())
            ts = int(time.time())
            filename = f"{clean_name}_{ts}.md"
            offload_file = scratch_dir / filename
            offload_file.write_text(content, encoding="utf-8")
            rel_path = str(offload_file.relative_to(clean_workspace)).replace("\\", "/")
            return f"Content offloaded to `/{rel_path}` ({len(content)} characters, {len(content.splitlines())} lines)."
        except Exception as exc:
            return f"Could not offload content: {str(exc)}"

    return [code_interpreter, verify_task, create_plan, update_plan, update_memory, offload_context]
