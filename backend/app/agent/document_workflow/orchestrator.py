import logging
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.backends.state import StateBackend
from app.backends.filesystem import FilesystemBackend
from app.mcp import OUTPUT_DIR

from app.agent.document_workflow.state import DocumentGenerationState, TaskLifecycle, SectionTask
from app.agent.document_workflow.complexity import ComplexityAnalyzer, ComplexityLevel
from app.agent.document_workflow.decomposer import TaskDecomposer
from app.agent.document_workflow.subagents import AsyncContentSubAgentRunner
from app.agent.document_workflow.integrator import ContentIntegrator
from app.agent.document_workflow.validator import SemanticContentValidator, ArtifactValidator
from app.agent.document_workflow.repair import TargetedRepairManager
from app.agent.document_workflow.discovery import DynamicSkillDiscovery
from app.agent.document_workflow.provenance import SourceProvenanceTracker

logger = logging.getLogger("app.agent.document_workflow.orchestrator")


class DocumentWorkflowOrchestrator:
    """
    Master orchestrator implementing the Deep Agents Intelligent Document Generation Protocol.
    Features:
    - StateBackend checkpointing across every lifecycle transition
    - Anti-overengineering: Small tasks use primary agent directly; complex tasks decompose
    - Async section sub-agents with failure isolation
    - Content integrator with deduplication
    - Pre-sandbox semantic validator and targeted section repair
    - Post-sandbox physical artifact validator
    - Resume / Recovery from StateBackend
    """

    def __init__(
        self,
        state_backend: Optional[StateBackend] = None,
        fs_backend: Optional[FilesystemBackend] = None,
        max_repairs: int = 2
    ):
        self.state_backend = state_backend or StateBackend()
        self.fs_backend = fs_backend
        self.repair_manager = TargetedRepairManager(max_repairs=max_repairs)

    async def execute_workflow(
        self,
        query: str,
        doc_format: str,
        user_id: Optional[int] = None,
        thread_id: Optional[str] = None,
        document_context: str = "",
        existing_plan: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        task_id = task_id or f"doc_{uuid.uuid4().hex[:10]}"
        logger.info(f"Starting Document Workflow task_id={task_id} format={doc_format}")

        # Check for resumption
        resumed_state = DocumentGenerationState.load(task_id, self.state_backend)
        if resumed_state and resumed_state.overall_status not in [TaskLifecycle.COMPLETED, TaskLifecycle.FAILED]:
            state = resumed_state
            logger.info(f"Resuming existing task {task_id} from state: {state.overall_status.value}")
        else:
            state = DocumentGenerationState(
                task_id=task_id,
                user_id=user_id,
                original_query=query,
                document_type=doc_format,
            )

        # 1. State: CREATED -> ANALYZING
        state.transition_to(TaskLifecycle.ANALYZING, "Analyzing query and scope")
        state.persist(self.state_backend)

        # Query analysis & Scope Lock
        scope_lock = {
            "must_include": [query.strip()],
            "may_include": ["Directly relevant domain and technical details"],
            "must_not_include": ["Generic conclusions", "Unrequested marketing filler", "Placeholders"]
        }
        state.scope_lock = scope_lock

        # 2. State: SKILL_SELECTION
        state.transition_to(TaskLifecycle.SKILL_SELECTION, "Discovering skills")
        skills = DynamicSkillDiscovery.discover_skills(query, doc_format)
        state.selected_skills = [s["name"] for s in skills]
        state.persist(self.state_backend)

        # 3. State: PLANNING
        state.transition_to(TaskLifecycle.PLANNING, "Formulating document plan")
        doc_plan = existing_plan
        if not doc_plan:
            from app.agent.content_planner import plan_and_generate_content
            doc_plan = await plan_and_generate_content(query, doc_format, document_context)

        if not isinstance(doc_plan, dict):
            doc_plan = {
                "topic": query,
                "title": query[:40],
                "sections": [{"heading": "Overview", "paragraphs": [str(doc_plan)]}],
            }

        state.document_plan = doc_plan
        state.persist(self.state_backend)

        # 4. Complexity Analysis
        complexity_info = await ComplexityAnalyzer.aanalyze(query, doc_format, doc_plan, document_context)
        use_async = complexity_info["use_async_subagents"]
        state.query_analysis["complexity"] = complexity_info

        # 5. State: DECOMPOSING & GENERATING
        if use_async:
            state.transition_to(TaskLifecycle.DECOMPOSING, "Decomposing into section tasks")
            section_tasks = TaskDecomposer.decompose(doc_plan, scope_lock, state.selected_skills)
            state.tasks = {t.task_id: {"title": t.title, "status": t.status} for t in section_tasks}
            state.persist(self.state_backend)

            state.transition_to(TaskLifecycle.GENERATING, f"Running {len(section_tasks)} async section sub-agents")
            section_results = await AsyncContentSubAgentRunner.run_parallel_subagents(
                tasks=section_tasks,
                query=query,
                scope_lock=scope_lock,
                document_context=document_context,
            )
            state.generated_sections = section_results
            state.subagent_status = {r["task_id"]: r["status"] for r in section_results}
            state.persist(self.state_backend)

            # 6. State: INTEGRATING
            state.transition_to(TaskLifecycle.INTEGRATING, "Integrating subagent section outputs")
            integrated_content = ContentIntegrator.integrate(section_results, doc_plan, scope_lock)
            state.persist(self.state_backend)
        else:
            # Small task: Primary Agent directly
            state.transition_to(TaskLifecycle.GENERATING, "Primary Agent generating content directly")
            if not isinstance(doc_plan, dict):
                doc_plan = {
                    "topic": query,
                    "title": query[:40],
                    "sections": [{"heading": "Overview", "paragraphs": [str(doc_plan)]}],
                }
            integrated_content = doc_plan
            integrated_content["scope_lock"] = scope_lock
            state.generated_sections = [
                {"content": s if isinstance(s, dict) else {"heading": str(s), "paragraphs": []}}
                for s in doc_plan.get("sections", [])
            ]
            state.persist(self.state_backend)

        # 7. State: VALIDATING (Pre-sandbox semantic validation)
        state.transition_to(TaskLifecycle.VALIDATING, "Pre-sandbox semantic validation")
        if not isinstance(integrated_content, dict):
            integrated_content = {
                "topic": query,
                "title": query[:40],
                "sections": [{"heading": "Overview", "paragraphs": [str(integrated_content)]}],
            }
        val_result = SemanticContentValidator.validate(integrated_content, scope_lock, query)
        state.validation_results = val_result
        state.persist(self.state_backend)

        # 8. State: REPAIRING (Targeted repair if validation failed)
        repair_attempts = 0
        while not val_result["valid"] and self.repair_manager.can_repair(repair_attempts):
            repair_attempts += 1
            state.transition_to(TaskLifecycle.REPAIRING, f"Targeted repair attempt {repair_attempts}")
            sections = integrated_content.get("sections") or []
            failed_indices = self.repair_manager.identify_failed_section_indices(val_result["issues"], sections)

            if failed_indices:
                for idx in failed_indices:
                    sections[idx] = self.repair_manager.repair_section_content(
                        sections[idx], val_result["issues"], scope_lock
                    )
            else:
                # General repair across sections
                for idx in range(len(sections)):
                    sections[idx] = self.repair_manager.repair_section_content(
                        sections[idx], val_result["issues"], scope_lock
                    )

            integrated_content["sections"] = sections
            val_result = SemanticContentValidator.validate(integrated_content, scope_lock, query)
            state.validation_results = val_result
            state.persist(self.state_backend)

        # 9. Determine target output path in FilesystemBackend
        title = integrated_content.get("title") if isinstance(integrated_content, dict) else None
        if not title:
            title = query[:30]
        from app.agent.subagents.document_agent import _suggest_filename, _build_fallback_document
        filename = _suggest_filename(query, doc_format, title=title)

        if self.fs_backend and user_id is not None:
            output_dir = self.fs_backend.get_user_generated_dir(user_id)
        else:
            output_dir = OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = (output_dir / filename).resolve()

        # 10. State: SANDBOX_RUNNING
        state.transition_to(TaskLifecycle.SANDBOX_RUNNING, "Executing sandbox document generator")
        state.persist(self.state_backend)

        # Build document deterministically using validated content
        build_ok = _build_fallback_document(doc_format, target_path, integrated_content)
        state.sandbox_status = "COMPLETED" if build_ok else "FALLBACK_FAILED"
        state.persist(self.state_backend)

        # 11. State: FILE_VALIDATING
        state.transition_to(TaskLifecycle.FILE_VALIDATING, "Validating output file integrity")
        file_val = ArtifactValidator.validate_file(target_path, doc_format)
        state.file_validation_status = "PASS" if file_val["valid"] else "FAIL"

        # 12. Final Artifact Metadata & Completion
        if file_val["valid"]:
            state.artifact_metadata = {
                "filename": target_path.name,
                "path": str(target_path),
                "type": doc_format,
                "size": file_val.get("size", 0),
                "validated": True,
                "task_id": task_id,
            }
            state.transition_to(TaskLifecycle.COMPLETED, f"Document deliverable verified: {target_path.name}")
        else:
            state.error = "; ".join(file_val.get("errors", ["File validation failed"]))
            state.transition_to(TaskLifecycle.FAILED, state.error)

        state.persist(self.state_backend)

        # Provenance records
        provenance = SourceProvenanceTracker().extract_from_plan(integrated_content, document_context)

        return {
            "task_id": task_id,
            "overall_status": state.overall_status.value,
            "success": (state.overall_status == TaskLifecycle.COMPLETED),
            "target_file": str(target_path),
            "content": integrated_content,
            "validation": file_val,
            "semantic_validation": val_result,
            "artifact_metadata": state.artifact_metadata,
            "provenance": provenance,
            "state_history": state.state_history,
        }
