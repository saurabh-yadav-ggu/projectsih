import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from app.config import settings
from app.backends.filesystem import FilesystemBackend
from app.agent.subagents.coding_agent import run_coding_agent
from app.agent.subagents.verification_agent import run_verification_agent
from app.agent.content_planner import plan_and_generate_content
from app.mcp import OUTPUT_DIR

from app.services.skill_manager import skill_manager

logger = logging.getLogger("app.agent.subagents.document")


def _suggest_filename(query: str, doc_format: str, title: Optional[str] = None) -> str:
    source = title or query
    source = re.sub(r"^(create|generate|make|build)\s+(a|an|the)?\s*", "", source, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", source[:40].strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_").lower() or "document"
    return f"{cleaned}.{doc_format}"


def _build_fallback_document(doc_format: str, target_path: Path, content_plan: Dict[str, Any]) -> bool:
    """
    Deterministic document builder adhering strictly to the
    DOCUMENT GENERATION — QUERY GROUNDING & CONTENT RELEVANCE PROTOCOL.
    Renders the exact Stage A structured content plan (topic, title, sections, tables, data)
    directly into the requested format (docx, pdf, xlsx, pptx, csv).
    """
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        title = content_plan.get("title") or "Executive Deliverable"
        subtitle = content_plan.get("subtitle") or ""
        sections = content_plan.get("sections") or []
        data_table = content_plan.get("data_table")

        if doc_format == "docx":
            from docx import Document
            from docx.shared import Inches, Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.enum.table import WD_TABLE_ALIGNMENT

            doc = Document()
            for s in doc.sections:
                s.top_margin = Inches(1)
                s.bottom_margin = Inches(1)
                s.left_margin = Inches(1)
                s.right_margin = Inches(1)

            # Title
            t_para = doc.add_paragraph()
            t_run = t_para.add_run(title)
            t_run.font.size = Pt(20)
            t_run.font.bold = True
            t_run.font.color.rgb = RGBColor(30, 41, 59)  # Slate 800
            t_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Subtitle
            if subtitle:
                sub = doc.add_paragraph()
                sub_run = sub.add_run(subtitle)
                sub_run.font.size = Pt(10.5)
                sub_run.font.italic = True
                sub_run.font.color.rgb = RGBColor(100, 116, 139)  # Slate 500
                sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
                doc.add_paragraph()  # Spacing

            # Render each grounded section
            for sec in sections:
                heading_text = sec.get("heading", "")
                if heading_text:
                    doc.add_heading(heading_text, level=1)

                for p in sec.get("paragraphs", []):
                    if p:
                        doc.add_paragraph(p)

                for b in sec.get("bullet_points", []):
                    if b:
                        doc.add_paragraph(f"• {b}")

                table_info = sec.get("table")
                if table_info and isinstance(table_info, dict):
                    headers = table_info.get("headers", [])
                    rows = table_info.get("rows", [])
                    if headers and rows:
                        t = doc.add_table(rows=1, cols=len(headers))
                        t.alignment = WD_TABLE_ALIGNMENT.CENTER
                        hdr_cells = t.rows[0].cells
                        for idx, h_text in enumerate(headers):
                            hdr_cells[idx].text = str(h_text)
                            for r in hdr_cells[idx].paragraphs[0].runs:
                                r.font.bold = True
                        for row_data in rows:
                            row_cells = t.add_row().cells
                            for c_idx, val in enumerate(row_data[:len(headers)]):
                                row_cells[c_idx].text = str(val)
                        doc.add_paragraph()  # Spacing after table

                callout = sec.get("callout")
                if callout:
                    c_para = doc.add_paragraph()
                    c_run = c_para.add_run(f"Note: {callout}")
                    c_run.font.italic = True
                    c_run.font.color.rgb = RGBColor(71, 85, 105)

            # Render data_table if present and not already displayed
            if data_table and isinstance(data_table, dict):
                headers = data_table.get("headers", [])
                rows = data_table.get("rows", [])
                if headers and rows:
                    doc.add_heading(f"Data Appendix: {data_table.get('sheet_name', 'Metrics')}", level=1)
                    dt = doc.add_table(rows=1, cols=len(headers))
                    dt.alignment = WD_TABLE_ALIGNMENT.CENTER
                    hdr_cells = dt.rows[0].cells
                    for idx, h_text in enumerate(headers):
                        hdr_cells[idx].text = str(h_text)
                        for r in hdr_cells[idx].paragraphs[0].runs:
                            r.font.bold = True
                    for row_data in rows:
                        row_cells = dt.add_row().cells
                        for c_idx, val in enumerate(row_data[:len(headers)]):
                            row_cells[c_idx].text = str(val)

            doc.save(str(target_path))
            return True

        elif doc_format == "pdf":
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

            doc = SimpleDocTemplate(
                str(target_path),
                pagesize=letter,
                rightMargin=54,
                leftMargin=54,
                topMargin=54,
                bottomMargin=54,
            )
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "DocTitle",
                parent=styles["Heading1"],
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#1E293B"),
                alignment=1,  # Center
                spaceAfter=6,
            )
            sub_style = ParagraphStyle(
                "DocSub",
                parent=styles["Normal"],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#64748B"),
                alignment=1,
                spaceAfter=14,
            )
            h1_style = ParagraphStyle(
                "SectionH1",
                parent=styles["Heading2"],
                fontSize=13,
                leading=17,
                textColor=colors.HexColor("#0F172A"),
                spaceBefore=12,
                spaceAfter=6,
            )
            body_style = ParagraphStyle(
                "BodyTextGrounded",
                parent=styles["Normal"],
                fontSize=9.5,
                leading=14,
                textColor=colors.HexColor("#334155"),
                spaceAfter=6,
            )
            bullet_style = ParagraphStyle(
                "BulletGrounded",
                parent=body_style,
                leftIndent=14,
                spaceAfter=4,
            )

            story = [Paragraph(title, title_style)]
            if subtitle:
                story.append(Paragraph(subtitle, sub_style))
            story.append(Spacer(1, 10))

            for sec in sections:
                h = sec.get("heading")
                if h:
                    story.append(Paragraph(h, h1_style))
                for p in sec.get("paragraphs", []):
                    story.append(Paragraph(p, body_style))
                for b in sec.get("bullet_points", []):
                    story.append(Paragraph(f"&bull; {b}", bullet_style))

                table_info = sec.get("table")
                if table_info and isinstance(table_info, dict):
                    headers = table_info.get("headers", [])
                    rows = table_info.get("rows", [])
                    if headers and rows:
                        table_matrix = [headers] + [[str(c) for c in r[:len(headers)]] for r in rows]
                        t = Table(table_matrix, hAlign="CENTER")
                        t.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                        ]))
                        story.append(Spacer(1, 6))
                        story.append(t)
                        story.append(Spacer(1, 8))

            doc.build(story)
            return True

        elif doc_format == "xlsx":
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

            wb = openpyxl.Workbook()
            ws = wb.active
            sheet_title = "Data"
            headers: List[str] = []
            rows_data: List[List[Any]] = []

            if data_table and isinstance(data_table, dict):
                sheet_title = data_table.get("sheet_name", "Data")[:30]
                headers = data_table.get("headers", [])
                rows_data = data_table.get("rows", [])

            if not headers:
                # Find first table in sections
                for sec in sections:
                    t_info = sec.get("table")
                    if t_info and isinstance(t_info, dict) and t_info.get("headers"):
                        sheet_title = sec.get("heading", "Data")[:30]
                        headers = t_info.get("headers", [])
                        rows_data = t_info.get("rows", [])
                        break

            if not headers:
                headers = ["Section", "Scope / Details", "Information Status"]
                for sec in sections:
                    h = sec.get("heading", "General")
                    p_summary = sec.get("paragraphs", [""])[0][:100] if sec.get("paragraphs") else "Scope defined by user query"
                    rows_data.append([h, p_summary, "AVAILABLE" if p_summary else "NOT_AVAILABLE"])
                if not rows_data:
                    rows_data.append(["Document Scope", "Requested document content", "NOT_AVAILABLE"])

            ws.title = re.sub(r"[\\/*?:\[\]]", "_", sheet_title)
            ws.append(headers)

            hdr_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            hdr_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
            align_center = Alignment(horizontal="center", vertical="center")

            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_num)
                cell.fill = hdr_fill
                cell.font = hdr_font
                cell.alignment = align_center

            for row_idx, r in enumerate(rows_data, start=2):
                ws.append(r[:len(headers)])

            # Auto-fit column widths
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

            wb.save(str(target_path))
            return True

        elif doc_format == "pptx":
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor

            prs = Presentation()
            prs.slide_width = Inches(13.333)
            prs.slide_height = Inches(7.5)

            # Slide 1: Title Slide
            title_layout = prs.slide_layouts[0]
            slide1 = prs.slides.add_slide(title_layout)
            slide1.shapes.title.text = title
            if len(slide1.placeholders) > 1 and subtitle:
                slide1.placeholders[1].text = subtitle

            # Slide 2+: Section slides
            content_layout = prs.slide_layouts[1]
            for sec in sections:
                slide = prs.slides.add_slide(content_layout)
                slide.shapes.title.text = sec.get("heading", "Section Overview")
                body_shape = slide.placeholders[1]
                tf = body_shape.text_frame
                tf.word_wrap = True

                first = True
                for p in sec.get("paragraphs", []):
                    if first:
                        tf.text = p
                        first = False
                    else:
                        p_para = tf.add_paragraph()
                        p_para.text = p

                for b in sec.get("bullet_points", []):
                    bp = tf.add_paragraph()
                    bp.text = f"• {b}"
                    bp.level = 1

            prs.save(str(target_path))
            return True

        elif doc_format == "csv":
            import csv
            headers = []
            rows_data = []

            if data_table and isinstance(data_table, dict):
                headers = data_table.get("headers", [])
                rows_data = data_table.get("rows", [])

            if not headers:
                for sec in sections:
                    t_info = sec.get("table")
                    if t_info and isinstance(t_info, dict) and t_info.get("headers"):
                        headers = t_info.get("headers", [])
                        rows_data = t_info.get("rows", [])
                        break

            if not headers:
                headers = ["Section", "Scope / Details", "Information Status"]
                for sec in sections:
                    h = sec.get("heading", "General")
                    p_summary = sec.get("paragraphs", [""])[0][:100] if sec.get("paragraphs") else "Overview"
                    rows_data.append([h, p_summary, "AVAILABLE" if p_summary else "NOT_AVAILABLE"])
                if not rows_data:
                    rows_data.append(["Document Scope", "Requested document content", "NOT_AVAILABLE"])

            with open(target_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for r in rows_data:
                    writer.writerow(r[:len(headers)])
            return True

    except Exception as e:
        logger.error(f"Deterministic grounded fallback builder failed: {e}", exc_info=True)
    return False


async def run_document_agent(
    query: str,
    user_id: Optional[int] = None,
    thread_id: Optional[str] = None,
    fs_backend: Optional[FilesystemBackend] = None,
    document_context: str = "",
    max_fix_attempts: int = 1,
) -> Dict[str, Any]:
    """
    Intelligent Document Generation Agent implementing the
    DEEP AGENTS PRECISION-FIRST DOCUMENT GENERATION PROTOCOL:

    Core Principle:
      - The USER decides WHAT the document contains.
      - The SKILLS decide HOW the document is created.
      - The ORCHESTRATOR controls the workflow.

    Workflow:
      1. Query Analysis & Scope Lock (Must Include, May Include, Must Not Include).
      2. Skill Discovery & Selection (docx, pptx, xlsx, pdf, csv).
      3. Stage A Content Generation & Validation (Zero placeholders, zero generic fluff).
      4. Stage B Sandbox Execution (AST sandbox execution via CodingAgent).
      5. File Validation & Targeted Repair (VerificationAgent audit and self-correction).
      6. FilesystemBackend Storage & Clean User Deliverable Response.
    """
    logger.info(f"Initiating Document Agent pipeline for: '{query[:60]}'")

    # 1. Match requirement against system and custom skills
    matched = skill_manager.match_skill(query)
    skill_blueprint = matched.get("skill") or {}
    doc_format = matched.get("format") or "docx"
    if "name" not in skill_blueprint and "title" in skill_blueprint:
        skill_blueprint["name"] = skill_blueprint["title"]
    if "name" not in skill_blueprint:
        skill_blueprint["name"] = f"{doc_format.upper()} Skill"
    if "content" not in skill_blueprint:
        skill_blueprint["content"] = matched.get("content") or ""

    # 2. Advanced Stateful Document Workflow Orchestrator
    try:
        from app.agent.document_workflow import DocumentWorkflowOrchestrator
        from app.backends.composite import get_composite_backend
        composite = get_composite_backend()

        orchestrator = DocumentWorkflowOrchestrator(
            state_backend=composite.state,
            fs_backend=fs_backend or composite.fs,
        )

        workflow_res = await orchestrator.execute_workflow(
            query=query,
            doc_format=doc_format,
            user_id=user_id,
            thread_id=thread_id,
            document_context=document_context,
        )

        if workflow_res.get("success"):
            target_path = Path(workflow_res["target_file"])
            wf_content = workflow_res.get("content")
            if not isinstance(wf_content, dict):
                wf_content = {"title": query[:40], "topic": query, "sections": []}

            doc_title = wf_content.get("title") or query[:40]
            doc_topic = wf_content.get("topic") or query

            art_dict = {
                "filename": target_path.name,
                "file_type": doc_format,
                "path": target_path.as_posix(),
                "size": target_path.stat().st_size if target_path.exists() else 0,
            }

            summary_text = (
                f"Generated {doc_format.upper()} document: **{target_path.name}**\n"
                f"• **Title**: {doc_title}\n"
                f"• **Topic & Scope**: {doc_topic}\n"
                f"• **Status**: PASS (Verified)\n"
                f"• **Output Location**: `{target_path.as_posix()}`{file_path_line}"
            )
            return {
                "agent": "document_agent",
                "format": doc_format,
                "success": True,
                "target_file": str(target_path),
                "artifacts": [art_dict],
                "verification": {"status": "PASS", "errors": []},
                "content_plan": wf_content,
                "response": summary_text,
                "error": None,
                "task_id": workflow_res.get("task_id"),
                "provenance": workflow_res.get("provenance", []),
            }
    except Exception as wf_err:
        logger.warning(f"Workflow orchestrator fallback to primary pipeline: {wf_err}")

    # Fallback to standard generation pipeline
    content_plan = await plan_and_generate_content(
        query=query,
        doc_format=doc_format,
        document_context=document_context,
    )
    doc_title = content_plan.get("title", "")

    suggested_filename = _suggest_filename(query, doc_format, title=doc_title)
    if fs_backend and user_id is not None:
        generated_dir = fs_backend.get_user_generated_dir(user_id)
    else:
        generated_dir = OUTPUT_DIR
    generated_dir.mkdir(parents=True, exist_ok=True)
    target_path = (generated_dir / suggested_filename).resolve()

    # 4. Assemble format rules and prompt for Stage B Coding Agent
    format_rules = ""
    if doc_format == "docx":
        format_rules = (
            "STRICT PYTHON-DOCX RULES (DO NOT VIOLATE):\n"
            "1. Do NOT import non-existent constants! In docx.enum.text, ONLY WD_ALIGN_PARAGRAPH exists. Do NOT import WD_HEADING, WD_ALIGN_VERTICAL, or WD_SECTION_START.\n"
            "2. Add headings using `doc.add_heading('Heading Text', level=1)`. There is NO WD_HEADING.\n"
            "3. Paragraph objects do NOT have a .font attribute. Apply font styling on Run objects: `run = p.add_run('text'); run.font.size = Pt(14)`.\n"
            "4. Cell objects do NOT have .add_run(). Set cell text using `cell.text = 'text'` or `p = cell.paragraphs[0]; run = p.add_run('text')`.\n"
            "5. To add a page break, use `doc.add_page_break()`. Never pass it to add_section().\n"
            "6. There is NO page_setup! Set page size directly on section: `section.page_width = Inches(8.5)`.\n"
            "7. Document objects do NOT have .pages or .page_count! Word calculates pagination dynamically at render time. NEVER access doc.pages or doc.page_count. For headers/footers, set static text: `doc.sections[0].footer.paragraphs[0].text = 'Footer text'`.\n"
            "8. doc.add_heading() returns a Paragraph, NOT a Run! Never do `heading.font.size`.\n"
            "9. Ensure all string literals are closed on the same line or use triple quotes \"\"\"...\"\"\".\n\n"
        )
    elif doc_format == "pdf":
        format_rules = (
            "STRICT REPORTLAB RULES:\n"
            "1. Use reportlab.platypus SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle or reportlab.pdfgen.canvas.\n"
            "2. Build the PDF directly and save to target_path.\n\n"
        )
    elif doc_format == "xlsx":
        format_rules = (
            "STRICT OPENPYXL RULES:\n"
            "1. Use openpyxl.Workbook, styles (Font, PatternFill, Alignment, Border).\n"
            "2. Auto-fit column widths and format header rows.\n"
            "3. Save workbook to target_path.\n\n"
        )
    elif doc_format == "pptx":
        format_rules = (
            "STRICT PYTHON-PPTX RULES:\n"
            "1. Use pptx.Presentation(). Set slide dimensions (16:9 or 4:3).\n"
            "2. Add Title slide and content slides for each planned section.\n"
            "3. Save presentation to target_path.\n\n"
        )

    task_prompt = (
        f"You are the Shield AI Document Creation Agent (Stage B - Document Builder).\n"
        f"PROTOCOL: Implement the DOCUMENT GENERATION — QUERY GROUNDING & CONTENT RELEVANCE PROTOCOL.\n"
        f"Stage A has authored the topic-grounded content plan below. Your task is to write Python code to format and render this EXACT content into a pristine {doc_format.upper()} file.\n"
        f"DO NOT replace, omit, or invent different content. Render all sections, paragraphs, tables, and metrics accurately.\n\n"
        f"Target output file: r'{str(target_path)}'\n"
        f"IMPORTANT: The script MUST save the finished document to: r'{str(target_path)}'\n\n"
        f"{format_rules}"
        f"--- STAGE A GROUNDED CONTENT PLAN (JSON) ---\n"
        f"{json.dumps(content_plan, indent=2)}\n"
        f"--- END CONTENT PLAN ---\n\n"
        f"--- APPLIED SKILL GUIDELINES ({skill_blueprint['name']}) ---\n"
        f"{skill_blueprint['content']}\n"
        f"--- END SKILL GUIDELINES ---\n\n"
        f"Output executable Python code to generate and save the document to target_path."
    )

    # 5. Execute via CodingAgent
    coding_res = await run_coding_agent(
        task_description=task_prompt,
        workspace_path=generated_dir,
        max_retries=2,
    )

    # 6. Grounded Fallback: If sandbox script failed, render structured content plan directly
    if not target_path.exists():
        logger.info(f"Target document not found after script execution; invoking grounded fallback builder for {doc_format}.")
        _build_fallback_document(doc_format, target_path, content_plan)

    created_artifacts = []
    if target_path.exists():
        created_artifacts.append(str(target_path))
    elif coding_res.get("artifacts"):
        created_artifacts.extend(coding_res["artifacts"])

    # 7. Verification phase
    verification_res = await run_verification_agent(
        artifact_paths=created_artifacts,
        user_id=user_id,
        thread_id=thread_id,
    )

    # 8. Self-correction loop if verification failed
    if verification_res["status"] != "PASS" and max_fix_attempts > 0:
        logger.warning(f"Verification failed: {verification_res['errors']}. Attempting fix...")
        fix_prompt = (
            f"The previously generated document failed verification.\n"
            f"Errors detected: {'; '.join(verification_res['errors'])}\n"
            f"Fix the Python script to address these errors and regenerate the document at: r'{str(target_path)}'."
        )
        coding_res = await run_coding_agent(
            task_description=fix_prompt,
            workspace_path=generated_dir,
            context_code=coding_res.get("code", ""),
            max_retries=1,
        )
        if not target_path.exists():
            _build_fallback_document(doc_format, target_path, content_plan)

        if target_path.exists() and str(target_path) not in created_artifacts:
            created_artifacts = [str(target_path)]

        verification_res = await run_verification_agent(
            artifact_paths=created_artifacts,
            user_id=user_id,
            thread_id=thread_id,
        )

    final_status = verification_res["status"]
    file_path_line = f"\n\nFilePath: {target_path.as_posix()}" if target_path.exists() else ""

    # Concise description respecting Section 20 of the protocol
    section_names = []
    if isinstance(content_plan, dict):
        for s in content_plan.get("sections", []):
            if isinstance(s, dict) and s.get("heading"):
                section_names.append(s["heading"])
            elif isinstance(s, str):
                section_names.append(s)

    sections_str = ", ".join(section_names[:4]) if section_names else "detailed sections and metrics"

    art_list = []
    for art in created_artifacts:
        if isinstance(art, dict):
            art_list.append(art)
        elif isinstance(art, str):
            p = Path(art)
            art_list.append({
                "filename": p.name,
                "file_type": doc_format,
                "path": str(p),
                "size": p.stat().st_size if p.exists() else 0,
            })

    summary_text = (
        f"Generated {doc_format.upper()} document: **{target_path.name}**\n"
        f"• **Title**: {doc_title}\n"
        f"• **Topic & Scope**: {content_plan.get('topic', query) if isinstance(content_plan, dict) else query}\n"
        f"• **Coverage**: Includes {sections_str}.\n"
        f"• **Status**: {final_status} (Verified)\n"
        f"• **Output Location**: `{target_path.as_posix()}`{file_path_line}"
    )

    return {
        "agent": "document_agent",
        "format": doc_format,
        "success": (final_status == "PASS"),
        "target_file": str(target_path),
        "artifacts": art_list,
        "verification": verification_res,
        "content_plan": content_plan,
        "response": summary_text,
        "error": None if final_status == "PASS" else "; ".join(verification_res.get("errors", [])),
    }
