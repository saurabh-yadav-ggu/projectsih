import pytest
import asyncio
from pathlib import Path
from docx import Document
import openpyxl
from pptx import Presentation
from pypdf import PdfReader

from app.agent.content_planner import (
    _build_deterministic_grounded_content,
    _validate_and_clean_content,
)
from app.agent.subagents.document_agent import (
    _build_fallback_document,
)
from app.agent.document_workflow.state import (
    SectionTask,
    InformationAvailability,
)
from app.agent.document_workflow.subagents import AsyncContentSubAgentRunner
from app.agent.document_workflow.repair import TargetedRepairManager
from app.agent.document_workflow.provenance import SourceProvenanceTracker
from app.agent.planner import _detect_format_from_query, generate_execution_plan
from app.services.skill_manager import skill_manager
from app.vision import analyze_image


def test_no_fake_metrics_or_budgets_in_deterministic_content():
    """Verify that _build_deterministic_grounded_content does not invent dollar figures or fake metrics."""
    query = "Create a report on Amazon KDP business opportunities in India"
    content = _build_deterministic_grounded_content(query, doc_format="docx")

    # Serialize content to inspect all text
    import json
    content_str = json.dumps(content)

    # 1. No fake financial figures
    assert "$15,000" not in content_str
    assert "$30,000" not in content_str
    assert "$10,000" not in content_str
    assert "$5,000" not in content_str
    assert "185%" not in content_str
    assert "94.5%" not in content_str
    assert "92%" not in content_str

    # 2. No fake company subtitle branding
    assert "Prepared by Shield AI Sovereign Document Engine" not in content_str

    # 3. Preserves query grounding and section count
    assert "Amazon Kdp" in content["title"]
    assert len(content["sections"]) >= 3

    # 4. Explicitly reports unavailable information where source data is needed
    sec3 = content["sections"][2]
    assert sec3["heading"] == "3. Data & Metric Verification"
    table_rows = sec3["table"]["rows"]
    assert any("Information unavailable from provided sources." in str(r) for r in table_rows)
    assert any("REQUIRES_SOURCE" in str(r) for r in table_rows)

    # 5. Data table explicitly reports missing info
    dt_rows = content["data_table"]["rows"]
    assert any("Information unavailable from provided sources." in str(r) for r in dt_rows)


def test_no_fake_branding_in_fallback_document(tmp_path: Path):
    """Verify that documents built via _build_fallback_document do not contain fabricated subtitles."""
    target_docx = tmp_path / "test_no_branding.docx"
    content_plan = {
        "title": "Clean Verified Analysis",
        "sections": [
            {
                "heading": "1. Scope",
                "paragraphs": ["Grounded content text."],
            }
        ]
    }
    ok = _build_fallback_document("docx", target_docx, content_plan)
    assert ok is True
    assert target_docx.exists()

    doc = Document(str(target_docx))
    full_text = " ".join(p.text for p in doc.paragraphs)
    assert "Prepared by Shield AI Sovereign Document Engine" not in full_text
    assert "Clean Verified Analysis" in full_text


def test_unavailable_information_reported_on_subagent_failure():
    """Verify that SectionTask failure explicitly reports unavailable information rather than fake filler."""
    async def _run():
        task = SectionTask(
            task_id="task_fail_01",
            section_id="financial_breakdown",
            title="Financial Breakdown",
            objective="Provide Q4 financial figures",
            retry_count=3,  # Exceeded max_retries
        )
        res = await AsyncContentSubAgentRunner.execute_task(
            task=task,
            query="Provide Q4 financial figures",
            scope_lock={"must_include": [], "must_not_include": []},
            max_retries=2,
        )
        assert res["status"] == "FAILED"
        paragraphs = res["content"]["paragraphs"]
        assert any("Information unavailable from provided sources" in p for p in paragraphs)
        assert not any("Section content for Financial Breakdown." == p for p in paragraphs)
        assert "Financial Breakdown" in res["missing_information"]

    asyncio.run(_run())


def test_repair_manager_explicitly_reports_unavailable_info_when_stripped():
    """Verify that when a section is stripped of placeholder content, it reports missing info rather than fake sentences."""
    repair_mgr = TargetedRepairManager(max_repairs=2)
    dirty_section = {
        "heading": "Market Sizing",
        "paragraphs": ["[Insert market size here]", "TODO: Add revenue numbers"],
        "bullet_points": ["<placeholder>"],
    }
    issues = [
        {"section_id": "section_1", "type": "PLACEHOLDER_DETECTED", "message": "Placeholder found"}
    ]
    repaired = repair_mgr.repair_section_content(dirty_section, issues, scope_lock={"must_not_include": []})
    assert repaired["paragraphs"] == ["Information unavailable from provided sources."]
    assert repaired["bullet_points"] == []


def test_provenance_tracker_does_not_hardcode_arbitrary_confidence():
    """Verify that SourceProvenanceTracker does not emit fabricated 0.85/0.95 confidence scores."""
    tracker = SourceProvenanceTracker()
    plan = {
        "sections": [
            {
                "heading": "1. Performance",
                "paragraphs": ["Revenue in Q3 was $5.2M according to internal filings."],
            }
        ]
    }
    doc_context = "--- Document Chunk 1 from annual_filing_2025.pdf ---\nRevenue in Q3 was $5.2M according to internal filings."
    records = tracker.extract_from_plan(plan, document_context=doc_context)
    assert len(records) == 1
    rec = records[0]
    # Source is extracted from real chunk metadata
    assert "annual_filing_2025.pdf" in rec["source"]
    assert rec["grounded"] is True
    assert rec["confidence"] == 1.0


def test_dynamic_format_detection_in_planner():
    """Verify that planner dynamically detects requested format instead of defaulting to docx."""
    assert _detect_format_from_query("Create an excel spreadsheet of student scores") == "xlsx"
    assert _detect_format_from_query("Make a powerpoint presentation for investor pitch") == "pptx"
    assert _detect_format_from_query("Export meeting notes to a pdf document") == "pdf"
    assert _detect_format_from_query("Generate a csv data table of sales") == "csv"
    assert _detect_format_from_query("Create a word doc of technical specifications") == "docx"

    async def _test_plan():
        plan = await generate_execution_plan("Create an excel spreadsheet of quarterly expenses")
        assert plan["intent"] == "document"
        assert plan["target_format"] == "xlsx"

    asyncio.run(_test_plan())


def test_skill_manager_dynamic_format_fallback():
    """Verify that skill manager fallback dynamically resolves the skill matching the requested target format."""
    res_xlsx = skill_manager.match_skill("generate budget document", format_hint="xlsx")
    assert res_xlsx["format"] == "xlsx"

    res_pdf = skill_manager.match_skill("generate executive overview", format_hint="pdf")
    assert res_pdf["format"] == "pdf"


def test_vision_reports_honest_status_when_no_multimodal_model(tmp_path: Path):
    """Verify that vision analysis optical report does not claim a local model is configuring in the background."""
    from PIL import Image
    test_img = tmp_path / "test_sample.png"
    img = Image.new("RGB", (200, 100), color="blue")
    img.save(test_img)

    result = analyze_image(str(test_img), question="Inspect this image")
    assert "Local neural vision model is configuring in the background" not in result
