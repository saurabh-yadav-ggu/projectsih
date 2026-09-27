import time
import io
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from langchain_core.documents import Document
from PIL import Image

import pymupdf  # PyMuPDF
from app.config import settings
from app.rag.page_detector import detect_page_type
from app.rag.normalizer import normalize_text
from app.rag.preprocessing import preprocess_image
from app.rag.ocr.factory import get_ocr_provider

logger = logging.getLogger("app.rag.pdf_processor")


class PDFProcessingResult:
    def __init__(
        self,
        documents: List[Document],
        document_id: str,
        filename: str,
        total_pages: int,
        text_pages: int,
        ocr_pages: int,
        failed_pages: int,
        stats: Dict[str, Any]
    ):
        self.documents = documents
        self.document_id = document_id
        self.filename = filename
        self.total_pages = total_pages
        self.text_pages = text_pages
        self.ocr_pages = ocr_pages
        self.failed_pages = failed_pages
        self.stats = stats


class PDFProcessor:
    """
    Production-grade hybrid PDF processor with per-page document-type detection.
    Processes pages incrementally, routing text-dense pages to direct extraction
    and scanned/image-only pages through local OCR and image preprocessing.
    """

    def __init__(
        self,
        min_text_length: Optional[int] = None,
        dpi: Optional[int] = None,
        ocr_enabled: Optional[bool] = None,
        preprocess: Optional[bool] = None,
        ocr_engine: Optional[str] = None
    ):
        self.min_text_length = min_text_length if min_text_length is not None else settings.OCR_MIN_TEXT_LENGTH
        self.dpi = dpi if dpi is not None else settings.OCR_DPI
        self.ocr_enabled = ocr_enabled if ocr_enabled is not None else settings.OCR_ENABLED
        self.preprocess = preprocess if preprocess is not None else settings.OCR_PREPROCESS
        self.ocr_engine = ocr_engine if ocr_engine is not None else settings.OCR_ENGINE

    def process_pdf(
        self,
        file_path: Union[str, Path],
        document_id: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> PDFProcessingResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"File must be a PDF, got: {path.suffix}")

        doc_id = document_id or uuid.uuid4().hex[:12]
        filename = path.name

        start_total = time.perf_counter()
        total_extraction_ms = 0.0
        total_ocr_ms = 0.0

        documents: List[Document] = []
        text_pages_count = 0
        ocr_pages_count = 0
        failed_pages_count = 0

        ocr_provider = get_ocr_provider(self.ocr_engine) if self.ocr_enabled else None

        try:
            pdf_doc = pymupdf.open(str(path))
        except Exception as e:
            logger.error(f"Failed to open PDF '{filename}': {e}", exc_info=True)
            raise ValueError(f"Corrupt or encrypted PDF '{filename}': {e}") from e

        total_pages = len(pdf_doc)

        try:
            for page_idx in range(total_pages):
                page = pdf_doc[page_idx]
                page_num_1based = page_idx + 1

                t0 = time.perf_counter()
                try:
                    native_text = page.get_text("text") or ""
                except Exception as extract_err:
                    logger.warning(f"Native text extraction failed for page {page_num_1based}: {extract_err}")
                    native_text = ""

                extraction_duration = (time.perf_counter() - t0) * 1000
                total_extraction_ms += extraction_duration

                detection = detect_page_type(native_text, min_text_length=self.min_text_length)

                page_text = ""
                extraction_method = "text"
                is_ocr = False
                ocr_conf = 1.0
                ocr_engine_name = "none"

                if not detection["is_scanned"]:
                    # Native text page
                    page_text = native_text
                    extraction_method = "text"
                    text_pages_count += 1
                else:
                    # Scanned or image-only page -> invoke local OCR
                    if self.ocr_enabled and ocr_provider and ocr_provider.is_available():
                        t_ocr = time.perf_counter()
                        try:
                            # Render page to image at specified DPI
                            pix = page.get_pixmap(dpi=self.dpi)
                            img_bytes = pix.tobytes("png")
                            pil_img = Image.open(io.BytesIO(img_bytes))

                            # Optional image preprocessing
                            if self.preprocess:
                                prep_img = preprocess_image(pil_img, enhance=True, denoise=True, deskew=True)
                                ocr_res = ocr_provider.extract_text(prep_img)
                            else:
                                ocr_res = ocr_provider.extract_text(pil_img)

                            ocr_duration = (time.perf_counter() - t_ocr) * 1000
                            total_ocr_ms += ocr_duration

                            page_text = ocr_res.text
                            extraction_method = "ocr"
                            is_ocr = True
                            ocr_conf = ocr_res.confidence
                            ocr_engine_name = ocr_res.engine
                            ocr_pages_count += 1

                            if ocr_conf < 0.4 and len(page_text) > 0:
                                logger.info(
                                    f"Low OCR confidence ({ocr_conf:.2f}) on '{filename}' page {page_num_1based}"
                                )

                        except Exception as ocr_err:
                            logger.error(f"OCR failed on page {page_num_1based}: {ocr_err}", exc_info=True)
                            page_text = native_text  # Fallback to whatever native text existed
                            extraction_method = "ocr_fallback"
                            failed_pages_count += 1
                    else:
                        page_text = native_text
                        extraction_method = "text_insufficient"
                        text_pages_count += 1

                # Normalize extracted text
                normalized = normalize_text(page_text)

                # Skip completely blank pages if neither native nor OCR found content
                if not normalized:
                    normalized = f"[Page {page_num_1based} contains no legible text or images]"

                meta = {
                    "source": str(path),
                    "filename": filename,
                    "document_id": doc_id,
                    "page_number": page_num_1based,
                    "page": page_idx,
                    "total_pages": total_pages,
                    "extraction_method": extraction_method,
                    "ocr": is_ocr,
                    "ocr_confidence": round(ocr_conf, 4) if is_ocr else None,
                    "ocr_engine": ocr_engine_name if is_ocr else None,
                    "char_count": len(normalized),
                }

                if extra_metadata:
                    meta.update(extra_metadata)

                doc_obj = Document(page_content=normalized, metadata=meta)
                documents.append(doc_obj)

        finally:
            pdf_doc.close()

        total_duration_ms = (time.perf_counter() - start_total) * 1000

        stats = {
            "total_duration_ms": round(total_duration_ms, 2),
            "extraction_duration_ms": round(total_extraction_ms, 2),
            "ocr_duration_ms": round(total_ocr_ms, 2),
            "avg_ms_per_page": round(total_duration_ms / total_pages, 2) if total_pages > 0 else 0,
            "total_pages": total_pages,
            "text_pages": text_pages_count,
            "ocr_pages": ocr_pages_count,
            "failed_pages": failed_pages_count,
        }

        logger.info(
            f"Processed '{filename}': {total_pages} pages ({text_pages_count} text, {ocr_pages_count} OCR) "
            f"in {total_duration_ms:.1f}ms"
        )

        return PDFProcessingResult(
            documents=documents,
            document_id=doc_id,
            filename=filename,
            total_pages=total_pages,
            text_pages=text_pages_count,
            ocr_pages=ocr_pages_count,
            failed_pages=failed_pages_count,
            stats=stats
        )
