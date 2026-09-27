from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Union
from PIL import Image
import numpy as np


@dataclass
class OCRResult:
    text: str
    confidence: float = 1.0  # 0.0 to 1.0
    boxes: List[Any] = field(default_factory=list)
    engine: str = "none"
    time_taken_ms: float = 0.0
    error: Optional[str] = None


class BaseOCRProvider(ABC):
    """Abstract Base Class for pluggable local OCR backends."""

    name: str = "base"

    @abstractmethod
    def extract_text(self, image: Union[Image.Image, np.ndarray, Path, str]) -> OCRResult:
        """Extract text and confidence score from an image."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the underlying OCR runtime and models are available."""
        pass
