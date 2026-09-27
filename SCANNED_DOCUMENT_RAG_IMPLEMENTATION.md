# Production-Grade Scanned-Document RAG Implementation

## 1. Executive Summary

This document details the production-grade scanned document and local OCR integration added to the existing LangChain RAG pipeline.

The implementation extends the existing RAG architecture without breaking text-based documents (PDF, DOCX, TXT, CSV, MD). It introduces an intelligent per-page detection system, a multi-stage local image preprocessing pipeline, local OCR engine abstraction (RapidOCR ONNX with Tesseract fallback), Unicode text normalization, metadata-preserving chunking, and verifiable source/page citation generation.

---

## 2. High-Level Architecture

```
                    Uploaded PDF / Document
                              │
                              ▼
                      PyMuPDF Document
                              │
               ┌──────────────┴──────────────┐
               │    Page-by-Page Iteration   │
               └──────────────┬──────────────┘
                              ▼
                     Native Text Extraction
                              │
                              ▼
                    Page-Type Detection
              (Length < threshold / corrupt font)
                        /           \
                      /               \
         [Clean Text Layer]       [Scanned / Image-Only]
                 │                         │
                 │                Render Image @ 300 DPI
                 │                         │
                 │                 Image Preprocessing
                 │             (Grayscale, CLAHE, Deskew)
                 │                         │
                 │                  Local OCR Engine
                 │             (RapidOCR / Tesseract)
                 │                         │
                 \                         /
                  \                       /
                   ▼                     ▼
                  Unicode & Artifact Normalizer
                               │
                               ▼
                   LangChain Document Object
             (page_number, ocr, confidence, method)
                               │
                               ▼
                    Per-Page Text Chunking
               (chunk_id: docId-p{page}-c{idx})
                               │
                               ▼
                  Ollama Embeddings Generation
                               │
                               ▼
                Chroma Vector Store (Scattered)
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
     Direct Retrieval                     Grounded Generation
  (Similarity Search +                  (LLM Response with
  Deduplication Scoping)               Accurate Page Citations)
```

---

## 3. Directory Structure & New Modules

```
backend/
├── app/
│   ├── config.py                         # Updated: OCR and preprocessing settings
│   ├── rag/
│   │   ├── __init__.py                   # Updated: Exports OCR and ingestion tools
│   │   ├── ingestion.py                  # Updated: PDFProcessor integration & deduplication
│   │   ├── retrieval.py                  # Updated: Page-level citations & [OCR] headers
│   │   ├── normalizer.py                 # NEW: Unicode NFKC & line-break normalizer
│   │   ├── page_detector.py              # NEW: Alphanumeric ratio & scan detector
│   │   ├── pdf_processor.py              # NEW: Per-page streaming pipeline & metrics
│   │   ├── preprocessing.py              # NEW: OpenCV contrast, denoise & deskew
│   │   └── ocr/
│   │       ├── __init__.py               # NEW: OCR provider exports
│   │       ├── base.py                   # NEW: BaseOCRProvider abstract interface
│   │       ├── rapidocr_provider.py      # NEW: RapidOCR ONNX provider (PaddleOCR-compatible)
│   │       ├── tesseract_provider.py     # NEW: Pytesseract local provider
│   │       └── factory.py                # NEW: Provider factory with singleton caching
│   ├── agent/
│   │   └── subagents/
│   │       └── rag_agent.py              # Updated: Grounded citation instructions & return payload
│   └── routers/
│       └── upload.py                     # Updated: Returns page stats (text_pages, ocr_pages)
└── tests/
    └── test_scanned_document_rag.py      # NEW: 12-scenario automated verification test suite
```

---

## 4. Component Details

### 4.1. Configuration (`app/config.py`)

Configuration parameters are loaded through Pydantic BaseSettings and can be overridden via environment variables or `.env`:

| Key | Default | Description |
| :--- | :--- | :--- |
| `OCR_ENABLED` | `True` | Master switch for local OCR processing |
| `OCR_ENGINE` | `"paddleocr"` | Primary OCR engine (`"paddleocr"`, `"tesseract"`, `"auto"`) |
| `OCR_DPI` | `300` | Pixmap rasterization DPI for scanned page rendering |
| `OCR_MIN_TEXT_LENGTH` | `30` | Minimum character length before classifying page as scanned |
| `OCR_PREPROCESS` | `True` | Toggle for OpenCV deskew, contrast, and denoising |
| `OCR_LANGUAGE` | `"eng"` | OCR recognition language |
| `TESSERACT_CMD` | `"tesseract"` | Path to local Tesseract executable if used |

### 4.2. Document-Type & Scanned-Page Detection (`app/rag/page_detector.py`)

PDF pages are evaluated individually. A page is routed to OCR if either condition holds:
1. **Low Text Density**: Extracted text character count $< \text{OCR\_MIN\_TEXT\_LENGTH}$ (default 30 chars).
2. **Corrupted Font / Garbage Encoding**: When scanned documents have bad hidden OCR text layers (symbol fonts, unmapped ligatures), the alphanumeric ratio is calculated:
   $$\text{Ratio} = \frac{\text{alphanumeric characters}}{\text{non-whitespace characters}}$$
   If $\text{Ratio} < 0.4$, the native text is treated as corrupt, and the page is rerouted to OCR.

### 4.3. Image Preprocessing Pipeline (`app/rag/preprocessing.py`)

When a page requires OCR, it is rendered in-memory via PyMuPDF at high DPI (300 DPI) and passed through OpenCV filters:
- **Grayscale Conversion**: Eliminates color noise and paper tint.
- **Contrast Enhancement**: Applies Contrast Limited Adaptive Histogram Equalization (CLAHE) with `clipLimit=2.0`.
- **Median Denoising**: Removes salt-and-pepper scan artifacts and specks without blurring text edges.
- **Deskewing**: Uses minimum area bounding box on thresholded text pixels to detect and rectify tilt angles between $-45^\circ$ and $+45^\circ$.

### 4.4. Local OCR Provider Abstraction (`app/rag/ocr/`)

The OCR system uses an extensible provider pattern:

```python
class BaseOCRProvider(ABC):
    @abstractmethod
    def extract_text(self, image: Union[Image.Image, np.ndarray]) -> OCRResult:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
```

- **RapidOCR ONNX (`RapidOCRProvider`)**: Purely local ONNX runtime using PaddleOCR model weights. Performs text detection and recognition on CPU without external services. Computes line-by-line average confidence scores ($0.0 \dots 1.0$).
- **Tesseract (`TesseractOCRProvider`)**: Local fallback using `pytesseract` and image-to-data confidence extraction.
- **Factory (`get_ocr_provider`)**: Singleton caching and `FallbackOCRProvider` ensuring seamless failover if one engine encounters an unhandled format.

### 4.5. Text Normalization (`app/rag/normalizer.py`)

Normalizes OCR and native text before chunking:
- Unicode NFKC normalization.
- Hyphenated line-break reconstruction (e.g., `oper-\nating` $\rightarrow$ `operating`).
- Broken single newline collapsing while retaining distinct paragraph breaks.
- Repeated whitespace collapsing.

### 4.6. PDF Processor (`app/rag/pdf_processor.py`)

- Streams pages incrementally to keep memory usage low.
- Enriches every page with complete audit metadata:
  ```json
  {
    "document_id": "8f3a1290e4b1",
    "source": "plant_inspection.pdf",
    "filename": "plant_inspection.pdf",
    "page_number": 24,
    "page": 23,
    "total_pages": 42,
    "extraction_method": "ocr",
    "ocr": true,
    "ocr_confidence": 0.942,
    "ocr_engine": "paddleocr"
  }
  ```
- Collects execution performance stats (`extraction_duration_ms`, `ocr_duration_ms`, `avg_ms_per_page`).

### 4.7. Chunking & Vector Ingestion (`app/rag/ingestion.py`)

- **Page Boundary Preservation**: Splits each page `Document` independently so text from page $N$ is never merged into page $N+1$.
- **Structured Chunk IDs**: Each chunk receives a deterministic ID:
  $$\text{chunk\_id} = \{\text{document\_id}\}\text{-p}\{\text{page\_number}\}\text{-c}\{\text{chunk\_index}\}$$
  Example: `abc123-p24-c03`.
- **Deduplication on Re-index**: `delete_document(filename, thread_id)` deletes any pre-existing chunks for that file in the thread before inserting new chunks, preventing duplicates.

### 4.8. Retrieval & Structured Citations (`app/rag/retrieval.py` & `app/agent/subagents/rag_agent.py`)

- **Context Chunk Formatting**: Context chunks passed to the LLM clearly show page numbers and OCR flags:
  ```text
  --- Document Chunk 1 from plant_inspection.pdf (Page 24) [OCR] ---
  Telemetry reading indicates bearing wear...
  ```
- **Citation Extraction (`retrieve_citations`)**: Extracts verified citations from metadata.
- **Citation Formatter (`format_citations`)**:
  - Single source:
    ```text
    Source: plant_inspection.pdf
    Page: 24
    ```
  - Multiple sources:
    ```text
    Sources:
    - plant_inspection.pdf — Page 24
    - inspection_report.pdf — Page 8
    ```
- **RAG Subagent**: Prompted to ground answers strictly in context chunk headers and output verifiable page numbers.

### 4.9. Upload API Endpoint (`app/routers/upload.py`)

When documents are uploaded via `/api/upload`, the response provides detailed document status:

```json
{
  "message": "Successfully indexed 'inspection_report.pdf' (18 chunks, 6 pages: 4 text, 2 OCR) into thread context.",
  "status": "READY",
  "document_id": "3d91cf02a8e1",
  "filename": "inspection_report.pdf",
  "file_path": ".../uploads/inspection_report.pdf",
  "is_image": false,
  "thread_id": "thread-402",
  "chunks_added": 18,
  "total_pages": 6,
  "ocr_pages": 2,
  "text_pages": 4,
  "pages": [
    {"page_number": 1, "extraction_method": "text", "ocr": false, "ocr_confidence": null},
    {"page_number": 2, "extraction_method": "ocr", "ocr": true, "ocr_confidence": 0.961}
  ]
}
```

---

## 5. Security & Privacy Guarantees

1. **100% Local Execution**: All OCR processing runs via local ONNX runtime and local CPU/GPU libraries. No data is transmitted to external OCR APIs.
2. **In-Memory Pixmap Lifecycle**: PDF page rendering uses PyMuPDF in-memory byte buffers (`pix.tobytes("png")`). Rendered images are never written to unmanaged disk folders.
3. **Thread and User Scoping**: Chroma vector store queries enforce strict metadata filters (`{"$and": [{"thread_id": ...}, {"user_id": ...}]}`).
4. **Content Sanitization**: Sensitive document text is omitted from server error logs.

---

## 6. Verification & Automated Test Suite

A comprehensive 12-scenario test suite was added to [backend/tests/test_scanned_document_rag.py](file:///d:/sih/project/backend/tests/test_scanned_document_rag.py):

| # | Test Scenario | Verified Behavior | Status |
| :-: | :--- | :--- | :-: |
| 1 | `test_normal_text_pdf` | Native text PDF extracts directly without triggering OCR; `ocr: False` | **PASSED** |
| 2 | `test_fully_scanned_pdf` | 100% raster-image PDF triggers OCR; extracts text with confidence > 0.8 | **PASSED** |
| 3 | `test_mixed_text_and_scanned_pdf` | Page 1 processed via text extraction, Page 2 processed via local OCR | **PASSED** |
| 4 | `test_empty_page` | Blank page handled safely without crash; marked with empty metadata | **PASSED** |
| 5 | `test_poor_quality_scan_preprocessing` | Noisy/blurred scan processed through CLAHE & denoising; text recognized | **PASSED** |
| 6 | `test_ocr_failure_fallback` | Graceful degradation to fallback state when OCR engine is disabled | **PASSED** |
| 7 | `test_multiple_page_document` | Multi-page document preserves sequential 1-based page numbers | **PASSED** |
| 8 | `test_metadata_chunk_preservation` | All chunks preserve `document_id`, `page_number`, and `chunk_id` | **PASSED** |
| 9 | `test_retrieval_from_ocr_content` | Chroma retrieves OCR chunks with `(Page 1) [OCR]` context header | **PASSED** |
| 10 | `test_citation_generation` | Single and multi-source citations formatted with exact page numbers | **PASSED** |
| 11 | `test_duplicate_document_reindexing` | Re-indexing identical file cleans old chunks; prevents duplicate entries | **PASSED** |
| 12 | `test_document_deletion` | `delete_document` deletes chunks from vector store; queries return empty | **PASSED** |

### Test Run Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.12, pytest-9.1.1, pluggy-1.6.0
collected 12 items

tests/test_scanned_document_rag.py::test_normal_text_pdf PASSED          [  8%]
tests/test_scanned_document_rag.py::test_fully_scanned_pdf PASSED        [ 16%]
tests/test_scanned_document_rag.py::test_mixed_text_and_scanned_pdf PASSED [ 25%]
tests/test_scanned_document_rag.py::test_empty_page PASSED               [ 33%]
tests/test_scanned_document_rag.py::test_poor_quality_scan_preprocessing PASSED [ 41%]
tests/test_scanned_document_rag.py::test_ocr_failure_fallback PASSED     [ 50%]
tests/test_scanned_document_rag.py::test_multiple_page_document PASSED   [ 58%]
tests/test_scanned_document_rag.py::test_metadata_chunk_preservation PASSED [ 66%]
tests/test_scanned_document_rag.py::test_retrieval_from_ocr_content PASSED [ 75%]
tests/test_scanned_document_rag.py::test_citation_generation PASSED      [ 83%]
tests/test_scanned_document_rag.py::test_duplicate_document_reindexing PASSED [ 91%]
tests/test_scanned_document_rag.py::test_document_deletion PASSED        [100%]

======================= 12 passed in 24.31s ========================
```
Existing system tests (`test_agent_routing.py`, `test_flow.py`, `test_router_rag.py`) also executed with **10 passed out of 10**.
