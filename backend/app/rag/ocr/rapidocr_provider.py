import time
import logging
from pathlib import Path
from typing import Union
from PIL import Image
import numpy as np

from app.rag.ocr.base import BaseOCRProvider, OCRResult

logger = logging.getLogger("app.rag.ocr.rapidocr")


class RapidOCRProvider(BaseOCRProvider):
    """
    Local PaddleOCR engine running on ONNX Runtime (RapidOCR).
    Completely local, private, CPU-optimized, and does not require cloud APIs or GPU.
    """

    name = "paddleocr"

    def __init__(self):
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
            logger.info("RapidOCR (PaddleOCR ONNX) engine initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to initialize RapidOCR engine: {e}")
            self._engine = None

    def is_available(self) -> bool:
        return self._engine is not None

    def extract_text(self, image: Union[Image.Image, np.ndarray, Path, str]) -> OCRResult:
        if not self.is_available():
            return OCRResult(
                text="",
                confidence=0.0,
                engine=self.name,
                error="RapidOCR engine is not available or failed to load."
            )

        start_time = time.perf_counter()
        try:
            # Prepare image as numpy array (RGB or Grayscale)
            if isinstance(image, (str, Path)):
                img_path = Path(image)
                if not img_path.exists():
                    return OCRResult(text="", confidence=0.0, engine=self.name, error=f"Image not found: {image}")
                pil_img = Image.open(str(img_path))
                img_np = np.array(pil_img)
            elif isinstance(image, Image.Image):
                img_np = np.array(image)
            elif isinstance(image, np.ndarray):
                img_np = image
            else:
                return OCRResult(text="", confidence=0.0, engine=self.name, error="Unsupported image type")

            # RapidOCR expects BGR or RGB array
            res, elapse = self._engine(img_np)
            duration_ms = (time.perf_counter() - start_time) * 1000

            if not res:
                return OCRResult(
                    text="",
                    confidence=1.0,
                    boxes=[],
                    engine=self.name,
                    time_taken_ms=duration_ms
                )

            extracted_lines = []
            confidences = []
            boxes = []

            for item in res:
                if len(item) >= 3:
                    box, line_text, score = item[0], item[1], float(item[2])
                    if line_text and line_text.strip():
                        extracted_lines.append(line_text.strip())
                        confidences.append(score)
                        boxes.append(box)

            full_text = "\n".join(extracted_lines)
            avg_conf = float(np.mean(confidences)) if confidences else 0.0

            return OCRResult(
                text=full_text,
                confidence=round(avg_conf, 4),
                boxes=boxes,
                engine=self.name,
                time_taken_ms=duration_ms
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"RapidOCR extraction error: {exc}", exc_info=True)
            return OCRResult(
                text="",
                confidence=0.0,
                engine=self.name,
                time_taken_ms=duration_ms,
                error=str(exc)
            )
