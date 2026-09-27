import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Normalizes extracted text (both native and OCR) prior to chunking and embedding.
    - Applies Unicode NFKC normalization.
    - Joins words broken across line breaks by hyphens (e.g., 'trans-\nmission' -> 'transmission').
    - Removes control characters and null bytes.
    - Collapses excessive blank lines (more than 2 consecutive newlines) into paragraph breaks.
    - Trims line-level trailing whitespace while preserving table delimiters ('|', tabs, commas).
    """
    if not text:
        return ""

    # 1. Unicode normalization
    normalized = unicodedata.normalize("NFKC", text)

    # 2. Strip null bytes and non-printable control characters (except tab, newline, carriage return)
    normalized = "".join(ch for ch in normalized if ch in ("\t", "\n", "\r") or (ord(ch) >= 32 and ord(ch) != 127))

    # 3. Fix broken hyphenated line breaks (e.g. 'instruc-\ntion' -> 'instruction')
    normalized = re.sub(r"([a-zA-Z]{2,})-\s*[\r\n]+\s*([a-zA-Z]{2,})", r"\1\2", normalized)

    # 4. Standardize newlines
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    # 5. Clean line whitespace: trim whitespace on each line without removing indentation or table formatting
    cleaned_lines = []
    for line in normalized.split("\n"):
        stripped_line = line.rstrip()
        # Collapse multiple spaces (except tabs)
        stripped_line = re.sub(r"[ \t]{2,}", " ", stripped_line)
        cleaned_lines.append(stripped_line)

    result = "\n".join(cleaned_lines)

    # 6. Collapse 3+ consecutive newlines into 2 (clean paragraph separation)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()
