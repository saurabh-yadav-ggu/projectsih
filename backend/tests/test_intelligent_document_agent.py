import pytest
import asyncio
from pathlib import Path

from app.backends.state import StateBackend
from app.backends.filesystem import FilesystemBackend
from app.agent.document_workflow.state import (
    DocumentGenerationState,
    TaskLifecycle,
    SectionTask,
)
from app.agent.document_workflow.complexity import (
    ComplexityAnalyzer,
    ComplexityLevel,
)
from app.agent.document_workflow.decomposer import TaskDecomposer
from app.agent.document_workflow.subagents import AsyncContentSubAgentRunner
from app.agent.document_workflow.integrator import ContentIntegrator
from app.agent.document_workflow.validator import (
    SemanticContentValidator,
    ArtifactValidator,
)
from app.agent.document_workflow.repair import TargetedRepairManager
from app.agent.document_workflow.discovery import DynamicSkillDiscovery
from app.agent.document_workflow.provenance import SourceProvenanceTracker
from app.agent.document_workflow.orchestrator import DocumentWorkflowOrchestrator


# ---------------------------------------------------------------------------
# 1. StateBackend Persistence & Lifecycle Transitions
# ---------------------------------------------------------------------------

def test_state_persistence_and_transitions():
    state_backend = StateBackend()
    state = DocumentGenerationState(
        task_id="task_test_001",
        user_id=1,
        original_query="Create a test report",
    )
    assert state.overall_status == TaskLifecycle.CREATED

    # Transition states
    state.transition_to(TaskLifecycle.ANALYZING, "Query analyzed")
    state.transition_to(TaskLifecycle.PLANNING, "Plan formulated")
    state.persist(state_backend)

    # Reload from backend
    loaded = DocumentGenerationState.load("task_test_001", state_backend)
    assert loaded is not None
    assert loaded.overall_status == TaskLifecycle.PLANNING
    assert len(loaded.state_history) == 2
    assert loaded.state_history[0]["from_state"] == "CREATED"
    assert loaded.state_history[0]["to_state"] == "ANALYZING"


def test_state_resume_skips_completed():
    state_backend = StateBackend()
    task1 = SectionTask(task_id="t1", section_id="sec1", title="Title 1", objective="Obj 1", status="COMPLETED")
    task2 = SectionTask(task_id="t2", section_id="sec2", title="Title 2", objective="Obj 2", status="PENDING")

    state = DocumentGenerationState(
        task_id="task_resume_002",
        tasks={
            "t1": {"status": "COMPLETED"},
            "t2": {"status": "PENDING"},
        },
        overall_status=TaskLifecycle.GENERATING,
    )
    state.persist(state_backend)

    loaded = DocumentGenerationState.load("task_resume_002", state_backend)
    assert loaded is not None
    assert loaded.tasks["t1"]["status"] == "COMPLETED"
    assert loaded.tasks["t2"]["status"] == "PENDING"


# ---------------------------------------------------------------------------
# 2. Complexity Analyzer
# ---------------------------------------------------------------------------

def test_complexity_analyzer_small_vs_large():
    # Small task: brief note or bullet points
    small_res = ComplexityAnalyzer.analyze(
        query="Quick bullet points on team lunch",
        doc_format="docx"
    )
    assert small_res["level"] == ComplexityLevel.SMALL
    assert not small_res["use_async_subagents"]

    # Large task: comprehensive proposal with multiple sections
    large_plan = {
        "sections": [
            {"heading": "1. Market Overview"},
            {"heading": "2. Competitive Landscape"},
            {"heading": "3. Technical Architecture"},
            {"heading": "4. Financial Model"},
            {"heading": "5. Implementation Roadmap"},
        ]
    }
    large_res = ComplexityAnalyzer.analyze(
        query="Comprehensive enterprise business proposal with 5 chapters and financial model",
        doc_format="docx",
        doc_plan=large_plan
    )
    assert large_res["level"] == ComplexityLevel.LARGE
    assert large_res["use_async_subagents"]


# ---------------------------------------------------------------------------
# 3. Task Decomposition
# ---------------------------------------------------------------------------

def test_task_decomposition_respects_scope_and_dependencies():
    plan = {
        "topic": "Sovereign AI Security",
        "sections": [
            {"heading": "1. Executive Summary", "paragraphs": ["Summary text."]},
            {"heading": "2. Security Architecture", "paragraphs": ["Architecture text."]},
            {"heading": "3. Implementation Roadmap", "paragraphs": ["Roadmap text."]},
        ],
        "data_table": {"headers": ["A", "B"], "rows": [[1, 2]]}
    }
    scope_lock = {
        "must_include": ["Sovereign AI"],
        "must_not_include": ["generic filler", "marketing fluff"]
    }

    tasks = TaskDecomposer.decompose(plan, scope_lock, selected_skills=["document-processing"])
    assert len(tasks) == 4  # 3 sections + 1 data_table
    assert tasks[0].section_id == "1_executive_summary"
    # Roadmap should depend on previous section
    assert len(tasks[2].dependencies) > 0
    assert any("generic filler" in c for c in tasks[0].scope_constraints)


# ---------------------------------------------------------------------------
# 4. Async Content Subagents & Single Section Retry
# ---------------------------------------------------------------------------

def test_async_parallel_generation_and_per_section_retry():
    async def _run():
        tasks = [
            SectionTask(task_id="t1", section_id="s1", title="Sec 1", objective="Obj 1", content={"heading": "Sec 1", "paragraphs": ["Pre-existing paragraph."]}),
            SectionTask(task_id="t2", section_id="s2", title="Sec 2", objective="Obj 2", content={"heading": "Sec 2", "paragraphs": ["Valid text."]}),
        ]
        results = await AsyncContentSubAgentRunner.run_parallel_subagents(
            tasks=tasks,
            query="Test query",
            scope_lock={"must_include": [], "must_not_include": []}
        )
        assert len(results) == 2
        assert all(r["status"] == "COMPLETED" for r in results)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 5. Content Integration & Deduplication
# ---------------------------------------------------------------------------

def test_content_integration_and_deduplication():
    section_results = [
        {
            "content": {
                "heading": "Section 1",
                "paragraphs": ["This is a unique point about architecture. Repeated sentence across sections."],
                "bullet_points": ["Bullet A"],
            },
            "sources_used": ["doc1"],
        },
        {
            "content": {
                "heading": "Section 2",
                "paragraphs": ["Repeated sentence across sections. A totally new insight."],
                "bullet_points": ["Bullet A", "Bullet B"],
            },
            "sources_used": ["doc2"],
        }
    ]
    base_plan = {"title": "Integrated Doc", "target_format": "docx"}
    scope_lock = {"must_include": ["architecture"], "must_not_include": []}

    integrated = ContentIntegrator.integrate(section_results, base_plan, scope_lock)
    assert len(integrated["sections"]) == 2
    # Check that duplicate bullet was scrubbed from Section 2
    sec2_bullets = integrated["sections"][1]["bullet_points"]
    assert "Bullet A" not in sec2_bullets
    assert "Bullet B" in sec2_bullets


# ---------------------------------------------------------------------------
# 6. Semantic Content Validation
# ---------------------------------------------------------------------------

def test_semantic_scope_validation_and_placeholder_detection():
    clean_doc = {
        "sections": [
            {
                "heading": "1. Overview",
                "paragraphs": ["Deep Agents sovereign architecture is fully verified."],
                "bullet_points": ["High fidelity metrics."],
            }
        ]
    }
    scope_lock = {
        "must_include": ["sovereign architecture"],
        "must_not_include": ["unrequested marketing"]
    }

    # Pass case
    pass_res = SemanticContentValidator.validate(clean_doc, scope_lock)
    assert pass_res["valid"]

    # Placeholder failure case
    ph_doc = {
        "sections": [
            {
                "heading": "1. Overview",
                "paragraphs": ["Here is [Insert text here] about architecture."],
                "bullet_points": [],
            }
        ]
    }
    ph_res = SemanticContentValidator.validate(ph_doc, scope_lock)
    assert not ph_res["valid"]
    assert any(i["type"] == "PLACEHOLDER_DETECTED" for i in ph_res["issues"])

    # Forbidden content failure case
    forbid_doc = {
        "sections": [
            {
                "heading": "1. Overview",
                "paragraphs": ["Contains unrequested marketing inside the body."],
                "bullet_points": [],
            }
        ]
    }
    forbid_res = SemanticContentValidator.validate(forbid_doc, scope_lock)
    assert not forbid_res["valid"]
    assert any(i["type"] == "FORBIDDEN_CONTENT_DETECTED" for i in forbid_res["issues"])


# ---------------------------------------------------------------------------
# 7. Targeted Repair
# ---------------------------------------------------------------------------

def test_targeted_repair_only_failed_section_with_limit():
    repair_manager = TargetedRepairManager(max_repairs=2)
    assert repair_manager.can_repair(0)
    assert repair_manager.can_repair(1)
    assert not repair_manager.can_repair(2)

    dirty_section = {
        "heading": "2. Technical Specs",
        "paragraphs": ["Valid analysis. [Insert details here] More info with unrequested marketing."],
        "bullet_points": ["TODO: check specs"]
    }
    issues = [
        {"section_id": "section_2", "type": "PLACEHOLDER_DETECTED", "message": "Placeholder found"}
    ]
    scope_lock = {"must_not_include": ["unrequested marketing"]}

    repaired = repair_manager.repair_section_content(dirty_section, issues, scope_lock)
    full_text = " ".join(repaired["paragraphs"] + repaired["bullet_points"])
    assert "[Insert details here]" not in full_text
    assert "TODO" not in full_text
    assert "unrequested marketing" not in full_text
    assert len(repair_manager.repair_history) == 1


# ---------------------------------------------------------------------------
# 8. Dynamic Skill Discovery & Source Provenance
# ---------------------------------------------------------------------------

def test_dynamic_skill_discovery():
    skills = DynamicSkillDiscovery.discover_skills(query="Generate an excel sheet", doc_format="xlsx")
    assert len(skills) >= 1
    assert any(s["format"] == "xlsx" for s in skills)


def test_source_provenance_tracking():
    tracker = SourceProvenanceTracker()
    tracker.record_claim(claim="Revenue grew by 42%", source="quarterly_report.pdf", location="p. 12", confidence=0.98)
    assert len(tracker.provenance_records) == 1
    rec = tracker.provenance_records[0]
    assert rec["source"] == "quarterly_report.pdf"
    assert rec["confidence"] == 0.98


# ---------------------------------------------------------------------------
# 9. Artifact Validation
# ---------------------------------------------------------------------------

def test_artifact_validation_docx_xlsx_pptx(tmp_path: Path):
    from app.agent.subagents.document_agent import _build_fallback_document

    sample_plan = {
        "title": "Verified Deliverable",
        "sections": [
            {
                "heading": "1. Core Summary",
                "paragraphs": ["Substantive verified paragraph."],
                "bullet_points": ["Verified point."],
            }
        ],
        "data_table": {
            "sheet_name": "Data",
            "headers": ["Metric", "Value"],
            "rows": [["Accuracy", 99]]
        }
    }

    # DOCX
    docx_path = tmp_path / "valid.docx"
    _build_fallback_document("docx", docx_path, sample_plan)
    v_docx = ArtifactValidator.validate_file(docx_path, "docx")
    assert v_docx["valid"]

    # XLSX
    xlsx_path = tmp_path / "valid.xlsx"
    _build_fallback_document("xlsx", xlsx_path, sample_plan)
    v_xlsx = ArtifactValidator.validate_file(xlsx_path, "xlsx")
    assert v_xlsx["valid"]

    # PPTX
    pptx_path = tmp_path / "valid.pptx"
    _build_fallback_document("pptx", pptx_path, sample_plan)
    v_pptx = ArtifactValidator.validate_file(pptx_path, "pptx")
    assert v_pptx["valid"]


# ---------------------------------------------------------------------------
# 10. End-to-End Orchestrator Workflow
# ---------------------------------------------------------------------------

def test_end_to_end_orchestrator_execution(tmp_path: Path):
    async def _run():
        fs = FilesystemBackend(root_dir=tmp_path / "workspace")
        state_backend = StateBackend()
        orchestrator = DocumentWorkflowOrchestrator(
            state_backend=state_backend,
            fs_backend=fs,
        )

        plan = {
            "title": "Automated Quality Deliverable",
            "topic": "Sovereign Document Architecture",
            "sections": [
                {
                    "heading": "1. Operational Context",
                    "paragraphs": ["Grounded context for sovereign execution."],
                    "bullet_points": ["Zero placeholder tolerance."],
                }
            ],
            "data_table": {
                "sheet_name": "Metrics",
                "headers": ["Target", "Status"],
                "rows": [["Delivery", "Verified"]]
            }
        }

        res = await orchestrator.execute_workflow(
            query="Produce verified report on Sovereign Document Architecture",
            doc_format="docx",
            user_id=1,
            existing_plan=plan,
        )

        assert res["success"]
        assert res["overall_status"] == TaskLifecycle.COMPLETED.value
        assert Path(res["target_file"]).exists()
        assert res["validation"]["valid"]
        assert len(res["state_history"]) >= 5

    asyncio.run(_run())


def test_robustness_with_string_inputs(tmp_path: Path):
    """Verifies that non-dict or raw string inputs do not raise 'str' object has no attribute 'get'."""
    # 1. ComplexityAnalyzer with raw string
    comp = ComplexityAnalyzer.analyze("simple quick note", "docx", doc_plan="not a dict")
    assert comp["level"] == ComplexityLevel.SMALL

    # 2. TaskDecomposer with raw string
    tasks = TaskDecomposer.decompose(document_plan="Raw text plan", scope_lock="Raw scope", selected_skills=[])
    assert len(tasks) >= 1
    assert tasks[0].status == "PENDING"

    # 3. TargetedRepairManager with string issues and sections
    indices = TargetedRepairManager.identify_failed_section_indices(
        validation_issues=["invalid string issue", {"section_id": "section_1"}],
        sections=["section 1 string", "section 2 string"]
    )
    assert indices == [0]

    # 4. SourceProvenanceTracker with string plan
    records = SourceProvenanceTracker().extract_from_plan("String plan", "")
    assert records == []

    # 5. Orchestrator with string existing_plan
    async def _run_str():
        fs = FilesystemBackend(root_dir=tmp_path / "workspace_str")
        state_backend = StateBackend()
        orchestrator = DocumentWorkflowOrchestrator(
            state_backend=state_backend,
            fs_backend=fs,
        )
        res = await orchestrator.execute_workflow(
            query="simple short document",
            doc_format="docx",
            user_id=1,
            existing_plan="String based plan from raw output",
        )
        assert res["success"]
        assert Path(res["target_file"]).exists()

    asyncio.run(_run_str())

