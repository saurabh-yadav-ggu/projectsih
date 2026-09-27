import re
from typing import Dict, Any
from app.config import settings


def detect_page_type(
    native_text: str,
    min_text_length: int = 30
) -> Dict[str, Any]:
    """
    Evaluates extracted native text to decide if a page requires local OCR.
    Handles:
    - Normal text pages
    - Fully scanned / image-only pages
    - Mixed pages
    - Empty or near-empty pages
    - Garbled / corrupt text encoding
    """
    cleaned = (native_text or "").strip()
    char_count = len(cleaned)
    words = re.findall(r"\b\w+\b", cleaned)
    word_count = len(words)

    # Empty or virtually empty text -> definitely scanned/image-only
    if char_count < min_text_length:
        return {
            "is_scanned": True,
            "extraction_method": "ocr",
            "reason": f"Text length ({char_count} chars) is below minimum threshold ({min_text_length})",
            "char_count": char_count,
            "word_count": word_count,
            "alpha_ratio": 0.0,
        }

    # Analyze alphanumeric density to detect garbage/symbol encoding errors
    alphanumeric_count = sum(1 for c in cleaned if c.isalnum())
    alpha_ratio = alphanumeric_count / char_count if char_count > 0 else 0.0

    # If alphanumeric ratio is abnormally low (< 25%), native parser likely failed or encountered corrupt font map
    if alpha_ratio < 0.25 and char_count < 100:
        return {
            "is_scanned": True,
            "extraction_method": "ocr",
            "reason": f"Low alphanumeric ratio ({alpha_ratio:.2f}); potential corrupt native text encoding",
            "char_count": char_count,
            "word_count": word_count,
            "alpha_ratio": round(alpha_ratio, 2),
        }

    # Sufficient native text available
    return {
        "is_scanned": False,
        "extraction_method": "text",
        "reason": "Sufficient native text extracted directly from PDF stream",
        "char_count": char_count,
        "word_count": word_count,
        "alpha_ratio": round(alpha_ratio, 2),
    }
