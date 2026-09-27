import logging
from typing import Optional, Dict

from app.config import settings
from app.rag.ocr.base import BaseOCRProvider, OCRResult
from app.rag.ocr.rapidocr_provider import RapidOCRProvider
from app.rag.ocr.tesseract_provider import TesseractOCRProvider

logger = logging.getLogger("app.rag.ocr.factory")

_PROVIDER_CACHE: Dict[str, BaseOCRProvider] = {}


class FallbackOCRProvider(BaseOCRProvider):
    name = "fallback"

    def is_available(self) -> bool:
        return True

    def extract_text(self, image) -> OCRResult:
        logger.warning("No local OCR engine is currently available to process scanned page.")
        return OCRResult(
            text="",
            confidence=0.0,
            engine=self.name,
            error="No OCR engine available. Install rapidocr-onnxruntime or configure Tesseract."
        )


def get_ocr_provider(engine_name: Optional[str] = None) -> BaseOCRProvider:
    """
    Factory resolving and caching the requested local OCR provider.
    Defaults to settings.OCR_ENGINE (e.g. 'rapidocr' or 'paddleocr').
    """
    target = (engine_name or settings.OCR_ENGINE or "rapidocr").lower()

    if target in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[target]

    provider: Optional[BaseOCRProvider] = None

    if target in ("tesseract",):
        tess = TesseractOCRProvider()
        if tess.is_available():
            provider = tess
        else:
            logger.warning("Tesseract requested but not available. Falling back to RapidOCR.")
            rapid = RapidOCRProvider()
            provider = rapid if rapid.is_available() else FallbackOCRProvider()

    elif target in ("rapidocr", "paddleocr"):
        rapid = RapidOCRProvider()
        if rapid.is_available():
            provider = rapid
        else:
            logger.warning("RapidOCR not available. Checking Tesseract fallback.")
            tess = TesseractOCRProvider()
            provider = tess if tess.is_available() else FallbackOCRProvider()

    else:
        # Default fallback
        rapid = RapidOCRProvider()
        provider = rapid if rapid.is_available() else FallbackOCRProvider()

    _PROVIDER_CACHE[target] = provider
    return provider
