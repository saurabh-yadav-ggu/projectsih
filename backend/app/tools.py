import io
import csv
from pathlib import Path
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from openpyxl import Workbook
from mcp_docgen.markdown_parser import parse_markdown
from mcp_docgen.docx_writer import write_docx
from mcp_docgen.pptx_writer import write_pptx
from mcp_docgen.pdf_writer import write_pdf
from mcp_docgen.html_writer import write_html

from app.rag import retrieve_context
from app.vision import analyze_image
from app.mcp import OUTPUT_DIR


@tool
def search_knowledge_base(query: str, thread_id: str = "") -> str:
    """Search internal knowledge base for information in uploaded documents, company knowledge, manuals, PDFs, and reports."""
    try:
        context = retrieve_context(query=query, k=6, thread_id=thread_id if thread_id else None)
        return context
    except Exception as e:
        return f"Knowledge base search failed: {str(e)}"


@tool
def analyze_image_tool(image_path: str, question: str = "Describe this image.") -> str:
    """Analyze an image using a local vision model to describe, inspect, or extract information."""
    try:
        result = analyze_image(image_path=image_path, question=question)
        return result
    except Exception as e:
        return f"Image analysis failed: {str(e)}"


@tool
def calculator(expression: str) -> str:
    """Calculate a mathematical expression (e.g. 25 * 48)."""
    try:
        allowed = {"__builtins__": {}}
        result = eval(expression, allowed, {})
        return str(result)
    except Exception:
        return "Invalid mathematical expression."


@tool
def save_as_document(
    filename: str,
    content: str = "",
    state: Annotated[dict, InjectedState] = None
) -> str:
    """Save generated text or conversation draft into a downloadable file (.docx, .xlsx, .pptx, .pdf, .html)."""
    try:
        fname = Path(filename).name
        target_path = OUTPUT_DIR / fname

        text = content
        if not text and state:
            messages = state.get("messages", [])
            for m in reversed(messages):
                if m.type == "ai" and m.content:
                    text = str(m.content)
                    break
        if not text and state:
            for m in reversed(messages):
                if m.type == "human" and m.content:
                    text = str(m.content)
                    break

        text = text.strip() if text else ""

        # Spreadsheet generation
        if fname.endswith(".xlsx"):
            wb = Workbook()
            ws = wb.active
            reader = csv.reader(io.StringIO(text))
            row_count = 0
            for row in reader:
                if not row:
                    continue
                parsed_row = []
                for cell in row:
                    cell_str = cell.strip()
                    try:
                        if "." in cell_str:
                            parsed_row.append(float(cell_str))
                        else:
                            parsed_row.append(int(cell_str))
                    except ValueError:
                        parsed_row.append(cell_str)
                ws.append(parsed_row)
                row_count += 1
            wb.save(target_path)
            return f"Successfully created Excel file with {row_count} rows. FilePath: {target_path.resolve().as_posix()}"

        blocks = parse_markdown(text)
        if fname.endswith(".pptx"):
            write_pptx(blocks, target_path)
        elif fname.endswith(".pdf"):
            write_pdf(blocks, target_path)
        elif fname.endswith(".html"):
            write_html(blocks, target_path)
        else:
            if not fname.endswith(".docx"):
                fname += ".docx"
                target_path = OUTPUT_DIR / fname
            write_docx(blocks, target_path)

        return f"Successfully created document. FilePath: {target_path.resolve().as_posix()}"
    except Exception as e:
        return f"Failed to save document: {str(e)}"


@tool
def create_excel_document(output_path: str, data: str, sheet_name: str = "Sheet1") -> str:
    """Create an Excel (.xlsx) spreadsheet from CSV text or table rows."""
    try:
        filename = Path(output_path).name
        if not filename.endswith(".xlsx"):
            filename += ".xlsx"
        target_path = OUTPUT_DIR / filename
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name or "Sheet1"
        reader = csv.reader(io.StringIO(data.strip()))
        row_count = 0
        for row in reader:
            if not row:
                continue
            parsed_row = []
            for cell in row:
                cell_val = cell.strip()
                try:
                    if "." in cell_val:
                        cell_val = float(cell_val)
                    else:
                        cell_val = int(cell_val)
                except ValueError:
                    pass
                parsed_row.append(cell_val)
            ws.append(parsed_row)
            row_count += 1
        wb.save(target_path)
        return f"Successfully created Excel spreadsheet with {row_count} rows. FilePath: {target_path.resolve().as_posix()}"
    except Exception as e:
        return f"Failed to create Excel file: {str(e)}"


@tool
def create_word_document(output_path: str, markdown_content: str, title: str = "") -> str:
    """Create a Word (.docx) document from Markdown text."""
    try:
        filename = Path(output_path).name
        if not filename.endswith(".docx"):
            filename += ".docx"
        target_path = OUTPUT_DIR / filename
        blocks = parse_markdown(markdown_content)
        write_docx(blocks, target_path, title=title if title else None)
        return f"Successfully created Word document. FilePath: {target_path.resolve().as_posix()}"
    except Exception as e:
        return f"Failed to create Word document: {str(e)}"


@tool
def create_presentation_document(output_path: str, markdown_content: str, title: str = "") -> str:
    """Create a PowerPoint (.pptx) presentation from Markdown with slides separated by ---."""
    try:
        filename = Path(output_path).name
        if not filename.endswith(".pptx"):
            filename += ".pptx"
        target_path = OUTPUT_DIR / filename
        blocks = parse_markdown(markdown_content)
        write_pptx(blocks, target_path, title=title if title else None)
        return f"Successfully created PowerPoint presentation. FilePath: {target_path.resolve().as_posix()}"
    except Exception as e:
        return f"Failed to create PowerPoint presentation: {str(e)}"


@tool
def create_pdf_document(output_path: str, markdown_content: str, title: str = "") -> str:
    """Create a PDF document from Markdown text."""
    try:
        filename = Path(output_path).name
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        target_path = OUTPUT_DIR / filename
        blocks = parse_markdown(markdown_content)
        write_pdf(blocks, target_path, title=title if title else None)
        return f"Successfully created PDF document. FilePath: {target_path.resolve().as_posix()}"
    except Exception as e:
        return f"Failed to create PDF document: {str(e)}"


@tool
def create_html_document(output_path: str, markdown_content: str, title: str = "") -> str:
    """Create a self-contained HTML page from Markdown text."""
    try:
        filename = Path(output_path).name
        if not filename.endswith(".html"):
            filename += ".html"
        target_path = OUTPUT_DIR / filename
        blocks = parse_markdown(markdown_content)
        write_html(blocks, target_path, title=title if title else None)
        return f"Successfully created HTML page. FilePath: {target_path.resolve().as_posix()}"
    except Exception as e:
        return f"Failed to create HTML page: {str(e)}"


local_tools = [
    search_knowledge_base,
    analyze_image_tool,
    calculator,
    save_as_document,
    create_excel_document,
    create_word_document,
    create_presentation_document,
    create_pdf_document,
    create_html_document,
]