import io
import os
import uuid
import pytest
import pymupdf
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.rag.pdf_processor import PDFProcessor
from app.rag.page_detector import detect_page_type
from app.rag.normalizer import normalize_text
from app.rag.preprocessing import preprocess_image
from app.rag.ocr.factory import get_ocr_provider
from app.rag.ingestion import (
    process_pdf,
    load_pdf,
    add_documents,
    delete_document,
)
from app.rag.retrieval import (
    retrieve_documents,
    retrieve_context,
    retrieve_citations,
    format_citations,
)


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


def create_native_text_pdf(path: Path, pages_text: list) -> Path:
    """Helper to create a PDF with native text layers."""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 72), text, fontsize=12)
    doc.save(str(path))
    doc.close()
    return path


def create_scanned_pdf(path: Path, pages_text: list) -> Path:
    """Helper to create a 100% scanned PDF where text is baked into raster images."""
    doc = pymupdf.open()
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font = ImageFont.load_default(size=24)

    for text in pages_text:
        img = Image.new("RGB", (800, 400), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((40, 100), text, fill=(0, 0, 0), font=font)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        page = doc.new_page(width=800, height=400)
        page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(str(path))
    doc.close()
    return path


# 1. Normal text PDF
def test_normal_text_pdf(temp_dir: Path):
    pdf_path = temp_dir / "normal_text.pdf"
    content = "This is a clean technical specification for an industrial turbine system."
    create_native_text_pdf(pdf_path, [content])

    processor = PDFProcessor()
    result = processor.process_pdf(pdf_path)

    assert result.total_pages == 1
    assert result.text_pages == 1
    assert result.ocr_pages == 0
    assert result.failed_pages == 0

    doc = result.documents[0]
    assert doc.metadata["ocr"] is False
    assert doc.metadata["extraction_method"] == "text"
    assert doc.metadata["page_number"] == 1
    assert "technical specification" in doc.page_content


# 2. Fully scanned PDF
def test_fully_scanned_pdf(temp_dir: Path):
    pdf_path = temp_dir / "fully_scanned.pdf"
    content = "Inspection Certificate 9081 Pass"
    create_scanned_pdf(pdf_path, [content])

    processor = PDFProcessor()
    result = processor.process_pdf(pdf_path)

    assert result.total_pages == 1
    assert result.ocr_pages == 1
    assert result.text_pages == 0

    doc = result.documents[0]
    assert doc.metadata["ocr"] is True
    assert doc.metadata["extraction_method"] == "ocr"
    assert doc.metadata["ocr_confidence"] is not None
    assert doc.metadata["ocr_confidence"] > 0.5
    assert "Inspection" in doc.page_content


# 3. Mixed text + scanned PDF
def test_mixed_text_and_scanned_pdf(temp_dir: Path):
    pdf_path = temp_dir / "mixed_document.pdf"
    doc = pymupdf.open()

    # Page 1: Native text
    p1 = doc.new_page(width=600, height=300)
    p1.insert_text((50, 72), "Chapter 1: Standard Operating Procedure for Pressure Relief Valves.", fontsize=12)

    # Page 2: Scanned raster image
    img = Image.new("RGB", (600, 300), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((40, 100), "Emergency Shutdown Trigger Checklist 402", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    p2 = doc.new_page(width=600, height=300)
    p2.insert_image(p2.rect, stream=buf.getvalue())

    doc.save(str(pdf_path))
    doc.close()

    processor = PDFProcessor()
    result = processor.process_pdf(pdf_path)

    assert result.total_pages == 2
    assert result.text_pages == 1
    assert result.ocr_pages == 1

    # Page 1: Text
    assert result.documents[0].metadata["page_number"] == 1
    assert result.documents[0].metadata["ocr"] is False
    assert result.documents[0].metadata["extraction_method"] == "text"
    assert "Standard Operating Procedure" in result.documents[0].page_content

    # Page 2: OCR
    assert result.documents[1].metadata["page_number"] == 2
    assert result.documents[1].metadata["ocr"] is True
    assert result.documents[1].metadata["extraction_method"] == "ocr"
    assert "Emergency Shutdown" in result.documents[1].page_content


# 4. Empty page
def test_empty_page(temp_dir: Path):
    pdf_path = temp_dir / "empty_page.pdf"
    doc = pymupdf.open()
    doc.new_page(width=500, height=500)  # Blank page
    doc.save(str(pdf_path))
    doc.close()

    processor = PDFProcessor()
    result = processor.process_pdf(pdf_path)

    assert result.total_pages == 1
    assert len(result.documents) == 1
    assert "contains no legible text" in result.documents[0].page_content.lower()


# 5. Poor-quality scan with image preprocessing
def test_poor_quality_scan_preprocessing(temp_dir: Path):
    pdf_path = temp_dir / "poor_scan.pdf"
    img = Image.new("RGB", (700, 250), color=(230, 230, 230))  # Grayish background
    d = ImageDraw.Draw(img)
    d.text((30, 80), "Hydraulic Pump Calibration Level 5", fill=(40, 40, 40))
    # Add slight blur to simulate scan noise
    noisy_img = img.filter(ImageFilter.GaussianBlur(radius=0.7))

    buf = io.BytesIO()
    noisy_img.save(buf, format="PNG")

    doc = pymupdf.open()
    p = doc.new_page(width=700, height=250)
    p.insert_image(p.rect, stream=buf.getvalue())
    doc.save(str(pdf_path))
    doc.close()

    # Process with preprocessing enabled
    processor = PDFProcessor(preprocess=True)
    result = processor.process_pdf(pdf_path)

    assert result.total_pages == 1
    assert result.ocr_pages == 1
    assert "Hydraulic" in result.documents[0].page_content or "Calibration" in result.documents[0].page_content


# 6. OCR failure handling
def test_ocr_failure_fallback(temp_dir: Path):
    pdf_path = temp_dir / "ocr_disabled.pdf"
    create_scanned_pdf(pdf_path, ["Confidential Record"])

    # Disable OCR explicitly
    processor = PDFProcessor(ocr_enabled=False)
    result = processor.process_pdf(pdf_path)

    assert result.total_pages == 1
    # Fallback to text_insufficient without crashing
    assert result.ocr_pages == 0
    assert result.documents[0].metadata["extraction_method"] == "text_insufficient"


# 7. Multiple-page document
def test_multiple_page_document(temp_dir: Path):
    pdf_path = temp_dir / "multi_page.pdf"
    pages = [
        "First section overview report",
        "Second section mechanical specifications",
        "Third section electrical schematics",
    ]
    create_native_text_pdf(pdf_path, pages)

    processor = PDFProcessor()
    result = processor.process_pdf(pdf_path)

    assert result.total_pages == 3
    for i, doc in enumerate(result.documents, 1):
        assert doc.metadata["page_number"] == i
        assert doc.metadata["page"] == i - 1
        assert doc.metadata["total_pages"] == 3


# 8. Metadata and page-number preservation in chunking
def test_metadata_chunk_preservation(temp_dir: Path):
    pdf_path = temp_dir / "chunk_meta.pdf"
    # Long text to force chunk splitting
    long_p1 = "Alpha Protocol. " + ("Turbine diagnostics data and telemetry readings. " * 30)
    long_p2 = "Beta Protocol. " + ("Coolant temperature regulation and safety measures. " * 30)
    create_native_text_pdf(pdf_path, [long_p1, long_p2])

    result = process_pdf(str(pdf_path), document_id="doc-test-123")
    assert len(result.documents) == 2

    thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"
    chunks_count = add_documents(result.documents, thread_id=thread_id, deduplicate=True)

    assert chunks_count >= 2

    # Verify chunks directly in vector store
    from app.rag.embeddings import vector_store
    data = vector_store.get(where={"thread_id": thread_id})
    metas = data.get("metadatas", [])

    assert len(metas) == chunks_count
    for m in metas:
        assert "document_id" in m
        assert "page_number" in m
        assert "chunk_id" in m
        assert m["chunk_id"].startswith("doc-test-123-p")


# 9. Retrieval from OCR content
def test_retrieval_from_ocr_content(temp_dir: Path):
    pdf_path = temp_dir / "scanned_for_rag.pdf"
    content = "Critical Telemetry Alert: Overheating indicates severe bearing wear at bearing four."
    create_scanned_pdf(pdf_path, [content])

    result = process_pdf(str(pdf_path), document_id="rag-ocr-doc")
    thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"
    add_documents(result.documents, thread_id=thread_id)

    # Retrieve context
    ctx = retrieve_context(query="bearing wear overheating alert", k=2, thread_id=thread_id)
    assert ("bearing" in ctx.lower() or "overheating" in ctx.lower())
    assert "(Page 1)" in ctx
    assert "[OCR]" in ctx


# 10. Citation generation
def test_citation_generation():
    citations_data = [
        {"source": "plant_inspection.pdf", "page": 24, "ocr": True, "extraction_method": "ocr"},
        {"source": "inspection_report.pdf", "page": 8, "ocr": False, "extraction_method": "text"},
    ]

    # Single source formatting
    single_formatted = format_citations([citations_data[0]])
    assert "Source: plant_inspection.pdf" in single_formatted
    assert "Page: 24" in single_formatted

    # Multiple source formatting
    multi_formatted = format_citations(citations_data)
    assert "Sources:" in multi_formatted
    assert "- plant_inspection.pdf — Page 24" in multi_formatted
    assert "- inspection_report.pdf — Page 8" in multi_formatted


# 11. Duplicate document re-indexing
def test_duplicate_document_reindexing(temp_dir: Path):
    pdf_path = temp_dir / "duplicate_test.pdf"
    create_native_text_pdf(pdf_path, ["Initial document version telemetry data."])

    thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"

    # Index 1st time
    res1 = process_pdf(str(pdf_path))
    count1 = add_documents(res1.documents, thread_id=thread_id, deduplicate=True)

    from app.rag.embeddings import vector_store
    data1 = vector_store.get(where={"thread_id": thread_id})
    assert len(data1.get("ids", [])) == count1

    # Re-index same file in same thread
    res2 = process_pdf(str(pdf_path))
    count2 = add_documents(res2.documents, thread_id=thread_id, deduplicate=True)

    data2 = vector_store.get(where={"thread_id": thread_id})
    # Should NOT be count1 + count2, should strictly equal count2
    assert len(data2.get("ids", [])) == count2


# 12. Document deletion
def test_document_deletion(temp_dir: Path):
    pdf_path = temp_dir / "deletion_target.pdf"
    create_native_text_pdf(pdf_path, ["Document destined for complete deletion."])

    thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"
    res = process_pdf(str(pdf_path))
    add_documents(res.documents, thread_id=thread_id)

    # Verify present
    from app.rag.embeddings import vector_store
    data_before = vector_store.get(where={"thread_id": thread_id})
    assert len(data_before.get("ids", [])) > 0

    # Delete
    deleted_count = delete_document(filename="deletion_target.pdf", thread_id=thread_id)
    assert deleted_count > 0

    # Verify gone
    data_after = vector_store.get(where={"thread_id": thread_id})
    assert len(data_after.get("ids", [])) == 0
