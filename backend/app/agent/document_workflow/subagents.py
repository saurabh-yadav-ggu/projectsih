import asyncio
import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.llm import get_llm
from app.agent.document_workflow.state import SectionTask

logger = logging.getLogger("app.agent.document_workflow.subagents")


SUBAGENT_SYSTEM_PROMPT = """You are a specialized Content Creation Sub-Agent operating under the Deep Agents Protocol.
You are a worker, NOT a decision maker.
YOUR SOLE RESPONSIBILITY is to author the specific section assigned to you.

STRICT RULES:
1. Stay strictly within your assigned section and the provided Scope Lock.
2. NEVER add unrequested sections, marketing filler, or generic conclusions.
3. NEVER invent facts, statistics, citations, or placeholder text ("[Insert here]", "TODO").
4. Return concrete, domain-specific text with actionable substance.
"""


class AsyncContentSubAgentRunner:
    """
    Coordinates asynchronous execution of SectionTasks.
    Executes independent tasks in parallel; tasks with dependencies wait for prerequisites.
    Implements single-section failure isolation with retry tracking.
    """

    @staticmethod
    async def execute_task(
        task: SectionTask,
        query: str,
        scope_lock: Dict[str, Any],
        document_context: str = "",
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """Executes a single section task with retry handling."""
        task.status = "RUNNING"
        task.max_retries = max_retries

        for attempt in range(task.retry_count, max_retries + 1):
            task.retry_count = attempt
            try:
                # If content is already validated and complete, skip LLM call
                if isinstance(task.content, dict) and (task.content.get("paragraphs") or task.content.get("data_table")):
                    task.status = "COMPLETED"
                    return {
                        "task_id": task.task_id,
                        "section_id": task.section_id,
                        "status": "COMPLETED",
                        "content": task.content,
                        "sources_used": ["reference_context"] if document_context else ["query"],
                        "warnings": [],
                        "missing_information": [],
                        "validation_notes": ["Grounded content preserved."],
                    }
                elif isinstance(task.content, str) and task.content.strip():
                    task.content = {"heading": task.title, "paragraphs": [task.content.strip()]}
                    task.status = "COMPLETED"
                    return {
                        "task_id": task.task_id,
                        "section_id": task.section_id,
                        "status": "COMPLETED",
                        "content": task.content,
                        "sources_used": ["reference_context"] if document_context else ["query"],
                        "warnings": [],
                        "missing_information": [],
                        "validation_notes": ["Grounded content preserved."],
                    }

                # Otherwise invoke LLM worker
                llm = get_llm(temperature=0.2)
                prompt = (
                    f"Overall Document Goal: {query}\n"
                    f"Assigned Section: {task.title}\n"
                    f"Section Objective: {task.objective}\n"
                    f"Section Requirements: {'; '.join(task.requirements)}\n"
                    f"Scope Constraints: {'; '.join(task.scope_constraints)}\n"
                    f"Context: {document_context[:1000] if document_context else 'None'}\n\n"
                    f"Author the section content with clear paragraphs and optional bullet points."
                )

                messages = [
                    SystemMessage(content=SUBAGENT_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
                resp = await llm.ainvoke(messages)
                text = resp.content if hasattr(resp, "content") else str(resp)

                paras = [p.strip() for p in text.split("\n\n") if p.strip() and not p.startswith("#")]
                generated_content = {
                    "heading": task.title,
                    "paragraphs": paras or [text.strip()],
                    "bullet_points": [],
                    "table": None,
                    "callout": None,
                }
                task.content = generated_content
                task.status = "COMPLETED"
                return {
                    "task_id": task.task_id,
                    "section_id": task.section_id,
                    "status": "COMPLETED",
                    "content": generated_content,
                    "sources_used": ["llm_grounding"],
                    "warnings": [],
                    "missing_information": [],
                    "validation_notes": [f"Authored {len(paras)} paragraph(s)."],
                }

            except Exception as e:
                logger.warning(f"Subagent attempt {attempt} failed for {task.task_id}: {e}")
                task.failure_reason = str(e)
                if attempt >= max_retries:
                    task.status = "FAILED"
                    unavailable_msg = f"Information unavailable from provided sources for {task.title}."
                    return {
                        "task_id": task.task_id,
                        "section_id": task.section_id,
                        "status": "FAILED",
                        "content": task.content or {"heading": task.title, "paragraphs": [unavailable_msg]},
                        "sources_used": [],
                        "warnings": [f"Execution failed after {max_retries} retries: {str(e)}"],
                        "missing_information": [task.title],
                        "validation_notes": ["Explicitly reported unavailable information."],
                    }
                await asyncio.sleep(0.5)

        task.status = "FAILED"
        return {
            "task_id": task.task_id,
            "section_id": task.section_id,
            "status": "FAILED",
            "content": task.content or {"heading": task.title, "paragraphs": [f"Information unavailable from provided sources for {task.title}."]},
            "sources_used": [],
            "warnings": ["Max retries exceeded"],
            "missing_information": [task.title],
            "validation_notes": ["Explicitly reported unavailable information."],
        }

    @classmethod
    async def run_parallel_subagents(
        cls,
        tasks: List[SectionTask],
        query: str,
        scope_lock: Dict[str, Any],
        document_context: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Executes independent tasks in parallel; tasks with dependencies wait for their prerequisites.
        """
        results_by_id: Dict[str, Dict[str, Any]] = {}
        completed_task_ids = set()

        # Partition into stages by dependency resolution
        remaining_tasks = list(tasks)
        max_loops = len(tasks) + 1

        while remaining_tasks and max_loops > 0:
            max_loops -= 1
            ready_tasks = [
                t for t in remaining_tasks
                if all(dep in completed_task_ids for dep in t.dependencies)
            ]

            if not ready_tasks:
                # Cycle or circular dep fallback: run the first task
                ready_tasks = [remaining_tasks[0]]

            # Run ready tasks in parallel
            batch_coros = [
                cls.execute_task(t, query, scope_lock, document_context)
                for t in ready_tasks
            ]
            batch_results = await asyncio.gather(*batch_coros, return_exceptions=False)

            for task, res in zip(ready_tasks, batch_results):
                results_by_id[task.task_id] = res
                completed_task_ids.add(task.task_id)
                remaining_tasks.remove(task)

        # Return results in original task ordering
        return [results_by_id[t.task_id] for t in tasks if t.task_id in results_by_id]
