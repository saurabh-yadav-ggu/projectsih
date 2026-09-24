import re
from typing import Dict, Any, List
import logging

from app.agent.document_workflow.state import SectionTask

logger = logging.getLogger("app.agent.document_workflow.decomposer")


class TaskDecomposer:
    """
    Decomposes an approved Document Plan into logical, independent SectionTask units.
    Strictly binds each task to the Scope Lock and tracks inter-section dependencies.
    """

    @staticmethod
    def decompose(
        document_plan: Dict[str, Any],
        scope_lock: Dict[str, Any],
        selected_skills: List[str]
    ) -> List[SectionTask]:
        if not isinstance(scope_lock, dict):
            scope_lock = {"must_include": [], "must_not_include": []}
        if not isinstance(document_plan, dict):
            document_plan = {"sections": [{"heading": "Overview", "paragraphs": [str(document_plan)]}]}

        sections = document_plan.get("sections") or []
        doc_topic = document_plan.get("topic", "")
        tasks: List[SectionTask] = []

        must_include = scope_lock.get("must_include", [])
        must_not_include = scope_lock.get("must_not_include", [])

        prev_task_id = None
        for idx, sec in enumerate(sections):
            if isinstance(sec, str):
                heading = sec
                paragraphs = []
                bullet_points = []
                has_table = False
                sec_dict = {"heading": sec, "paragraphs": [f"Details for {sec}."]}
            elif isinstance(sec, dict):
                heading = sec.get("heading", f"Section {idx + 1}")
                paragraphs = sec.get("paragraphs") or []
                bullet_points = sec.get("bullet_points") or []
                has_table = bool(sec.get("table"))
                sec_dict = sec
            else:
                heading = str(sec)
                paragraphs = []
                bullet_points = []
                has_table = False
                sec_dict = {"heading": heading}

            raw_id = re.sub(r"[^a-zA-Z0-9_]", "_", heading.lower())[:30]
            clean_sec_id = re.sub(r"_+", "_", raw_id).strip("_") or f"section_{idx + 1}"
            task_id = f"task_{idx + 1:02d}_{clean_sec_id}"

            # Formulate section objective
            objective = f"Author substantive, verified domain content for '{heading}' concerning {doc_topic}."
            
            # Formulate requirements specific to this section
            requirements = []
            if paragraphs:
                requirements.append(f"Produce {len(paragraphs)} domain-specific paragraph(s).")
            if bullet_points:
                requirements.append(f"Include key bullet points: {len(bullet_points)} item(s).")
            if has_table:
                requirements.append("Include structured comparison/data table with verified headers.")

            # Identify if section has dependencies (e.g., Conclusions or Recommendations depend on earlier analysis)
            dependencies = []
            heading_lower = heading.lower()
            if any(kw in heading_lower for kw in ["conclusion", "summary", "recommendation", "roadmap", "next step"]) and prev_task_id:
                dependencies.append(prev_task_id)

            task = SectionTask(
                task_id=task_id,
                section_id=clean_sec_id,
                title=heading,
                objective=objective,
                requirements=requirements or ["Provide domain-specific analysis and verified facts."],
                scope_constraints=[f"Never include: {item}" for item in must_not_include[:3]],
                dependencies=dependencies,
                required_skills=selected_skills or ["document-processing"],
                status="PENDING",
                content=sec,  # Initial template/plan content
            )
            tasks.append(task)
            prev_task_id = task_id

        # Also handle data_table if requested separately
        if document_plan.get("data_table"):
            tasks.append(SectionTask(
                task_id="task_data_table",
                section_id="data_table",
                title="Structured Data Table",
                objective="Format and verify numerical data table rows and columns.",
                requirements=["Ensure all headers and data rows align."],
                scope_constraints=["Zero fabricated columns."],
                dependencies=[],
                required_skills=selected_skills or ["document-processing"],
                status="PENDING",
                content={"data_table": document_plan["data_table"]},
            ))

        logger.info(f"Decomposed document plan into {len(tasks)} section task(s).")
        return tasks
