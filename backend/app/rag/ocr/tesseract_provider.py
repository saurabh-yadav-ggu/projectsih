import time
import logging
from pathlib import Path
from typing import Union
from PIL import Image
import numpy as np

from app.config import settings
from app.rag.ocr.base import BaseOCRProvider, OCRResult

logger = logging.getLogger("app.rag.ocr.tesseract")


class TesseractOCRProvider(BaseOCRProvider):
    """
    Local Tesseract OCR engine provider.
    Uses pytesseract with configurable language and tesseract binary path.
    """

    name = "tesseract"

    def __init__(self, lang: str = "eng", tesseract_cmd: str = ""):
        self.lang = lang or settings.OCR_LANGUAGE or "eng"
        self._cmd = tesseract_cmd or settings.TESSERACT_CMD
        self._available: bool = False
        self._init_engine()

    def _init_engine(self):
        try:
            import pytesseract
            if self._cmd:
                pytesseract.pytesseract.tesseract_cmd = self._cmd

            # Test invocation to check if binary is accessible
            _ = pytesseract.get_tesseract_version()
            self._available = True
            logger.info("Tesseract OCR engine is available.")
        except Exception as e:
            logger.info(f"Tesseract binary is not installed or not in PATH: {e}")
            self._available = False

    def is_available(self) -> bool:
        return self._available

    def extract_text(self, image: Union[Image.Image, np.ndarray, Path, str]) -> OCRResult:
        if not self.is_available():
            return OCRResult(
                text="",
                confidence=0.0,
                engine=self.name,
                error="Tesseract OCR binary is not installed or not accessible in PATH."
            )

        start_time = time.perf_counter()
        try:
            import pytesseract

            if isinstance(image, (str, Path)):
                pil_img = Image.open(str(image))
            elif isinstance(image, np.ndarray):
                pil_img = Image.fromarray(image)
            elif isinstance(image, Image.Image):
                pil_img = image
            else:
                return OCRResult(text="", confidence=0.0, engine=self.name, error="Unsupported image type")

            # Extract detailed data with confidences
            data = pytesseract.image_to_data(pil_img, lang=self.lang, output_type=pytesseract.Output.DICT)
            duration_ms = (time.perf_counter() - start_time) * 1000

            texts = data.get("text", [])
            confs = data.get("conf", [])

            words = []
            valid_confs = []

            for word, conf in zip(texts, confs):
                clean_w = str(word).strip()
                if clean_w:
                    words.append(clean_w)
                    try:
                        c_val = float(conf)
                        if c_val >= 0:
                            valid_confs.append(c_val / 100.0)
                    except (ValueError, TypeError):
                        pass

            full_text = " ".join(words)
            avg_conf = float(np.mean(valid_confs)) if valid_confs else 0.0

            return OCRResult(
                text=full_text,
                confidence=round(avg_conf, 4),
                boxes=[],
                engine=self.name,
                time_taken_ms=duration_ms
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Tesseract OCR error: {exc}", exc_info=True)
            return OCRResult(
                text="",
                confidence=0.0,
                engine=self.name,
                time_taken_ms=duration_ms,
                error=str(exc)
            )
