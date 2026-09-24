import json
import logging
import re
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger("app.core.json_utils")


def extract_clean_topic(query: str) -> str:
    """
    Extracts the core subject/topic from a natural language document generation query.
    Strips command prefixes, file formats, and length constraints.
    Preserves uppercase for common industry acronyms (AI, ML, API, etc.).
    
    Examples:
    - 'create a pdf file on how ai works in 10 page' -> 'How AI Works'
    - 'generate a 5 page report on artificial intelligence' -> 'Artificial Intelligence'
    - 'make a presentation on quarterly sales results' -> 'Quarterly Sales Results'
    - 'write a doc about machine learning and neural networks' -> 'Machine Learning and Neural Networks'
    - 'create an excel spreadsheet of company employees in 3 sheets' -> 'Company Employees'
    """
    if not query:
        return ""
        
    q = query.strip()
    
    # 1. Remove leading command / polite phrases / format specifiers
    lead_patterns = [
        r"^(?:please\s+)?(?:can\s+you\s+)?(?:could\s+you\s+)?(?:create|generate|make|build|write|draft|produce|prepare|compose|provide|explain|summarize|give\s+me)\s+(?:me\s+)?(?:\b(?:an|a|the)\b\s*)?",
        r"^(?:\b\d+\s*(?:pages?|slides?|sheets?)\s*(?:report|document|doc|presentation|overview|summary|guide|analysis)?\s*(?:on|about|of|for)?\s*)",
        r"^(?:(?:\b(?:new|complete|detailed|comprehensive|formal|professional|in-depth|short|brief)\b)\s*)+",
        r"^(?:(?:\b(?:pdf|docx|doc|excel|spreadsheet|sheets|presentation|slides|pptx|powerpoint|document|report|file|guide|handbook|manual|whitepaper|analysis|overview)\b)\s*(?:file|document|doc|report|sheet|presentation|deck)?\s*)",
        r"^(?:(?:\b(?:on|about|for|regarding|explaining|covering|detailing|discussing|describing|related\s+to|entitled|titled|of)\b)\s*)",
        r"^(?:\b(?:an|a|the)\b\s*)",
    ]
    
    changed = True
    while changed:
        orig = q
        for pat in lead_patterns:
            q = re.sub(pat, "", q, flags=re.IGNORECASE).strip()
        changed = (q != orig)

    # 2. Remove trailing constraints like "in 10 page", "in 5 pages", "of 10 pages", "as a pdf", "in docx format", etc.
    trail_patterns = [
        r"\s+(?:in|of|with|having|for)\s+\d+\s*(?:pages?|slides?|sheets?|paragraphs?|sections?|parts?)\b.*$",
        r"\s+in\s+\d+\s*page\b.*$",
        r"\s+(?:in|as)\s+(?:a\s+)?(?:pdf|docx|excel|sheet|presentation|pptx|slides|doc|document|file|format)\b.*$",
        r"\s+(?:format|please|thanks?|thank\s+you)\b.*$",
    ]
    for pat in trail_patterns:
        q = re.sub(pat, "", q, flags=re.IGNORECASE).strip()

    # If query was completely stripped, fall back to cleaned query
    if not q:
        q = query.strip()

    # 3. Capitalize words intelligently while respecting known acronyms
    acronyms = {
        "ai": "AI",
        "ml": "ML",
        "dl": "DL",
        "api": "API",
        "apis": "APIs",
        "llm": "LLM",
        "llms": "LLMs",
        "nlp": "NLP",
        "roi": "ROI",
        "it": "IT",
        "hr": "HR",
        "gpu": "GPU",
        "gpus": "GPUs",
        "cpu": "CPU",
        "cpus": "CPUs",
        "sql": "SQL",
        "nosql": "NoSQL",
        "iot": "IoT",
        "saas": "SaaS",
        "kpi": "KPI",
        "kpis": "KPIs",
        "ui": "UI",
        "ux": "UX",
        "rag": "RAG",
        "kdp": "Kdp",
    }
    
    words = q.split()
    formatted_words = []
    minor_words = {"a", "an", "the", "and", "but", "or", "for", "nor", "on", "at", "to", "by", "with", "in", "of"}
    for idx, w in enumerate(words):
        w_lower = w.lower()
        clean_w = re.sub(r"^[^\w]+|[^\w]+$", "", w_lower)
        if clean_w in acronyms:
            prefix = w[:len(w) - len(w.lstrip("^~`!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?"))]
            suffix = w[len(w.rstrip("^~`!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?")):]
            formatted_words.append(f"{prefix}{acronyms[clean_w]}{suffix}")
        elif idx > 0 and w_lower in minor_words:
            formatted_words.append(w_lower)
        else:
            formatted_words.append(w.capitalize())
            
    return " ".join(formatted_words)


def robust_json_loads(text: str) -> Union[Dict[str, Any], List[Any]]:
    """
    Robust JSON parser specifically engineered to handle common LLM output anomalies:
    - Markdown fences (```json ... ```)
    - Preamble or postamble conversational text
    - Trailing commas in objects and arrays
    - Python literal booleans/nulls (True, False, None)
    - Unescaped newlines/tabs inside string literals
    - Internal unescaped double quotes inside strings
    - Unbalanced closing braces/brackets resulting from token truncation
    """
    if not text or not isinstance(text, str):
        raise ValueError("Input must be a non-empty string")

    cleaned = text.strip()

    # 1. Strip markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # 2. Find outermost JSON object or array bounds
    start_brace = cleaned.find("{")
    start_bracket = cleaned.find("[")
    
    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        start_idx = start_brace
        end_idx = cleaned.rfind("}")
        if end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx:end_idx + 1]
        else:
            cleaned = cleaned[start_idx:]
    elif start_bracket != -1:
        start_idx = start_bracket
        end_idx = cleaned.rfind("]")
        if end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx:end_idx + 1]
        else:
            cleaned = cleaned[start_idx:]

    # Attempt 1: Direct standard load
    try:
        return json.loads(cleaned, strict=False)
    except Exception:
        pass

    # 3. Clean python booleans and nulls
    cleaned_norm = re.sub(r"\bTrue\b", "true", cleaned)
    cleaned_norm = re.sub(r"\bFalse\b", "false", cleaned_norm)
    cleaned_norm = re.sub(r"\bNone\b", "null", cleaned_norm)

    # 4. Remove trailing commas before } or ]
    cleaned_norm = re.sub(r",\s*([\]}])", r"\1", cleaned_norm)

    try:
        return json.loads(cleaned_norm, strict=False)
    except Exception:
        pass

    # 5. Fix unescaped quotes inside strings using scanner
    out = []
    in_string = False
    escaped = False
    i = 0
    n = len(cleaned_norm)

    while i < n:
        ch = cleaned_norm[i]
        if escaped:
            out.append(ch)
            escaped = False
            i += 1
            continue

        if ch == '\\':
            out.append(ch)
            escaped = True
            i += 1
            continue

        if ch == '"':
            if not in_string:
                in_string = True
                out.append(ch)
            else:
                # Look ahead to see if this quote really closes the string
                # Valid after closing quote in JSON: whitespace followed by :, ,, }, ], or EOF
                rest = cleaned_norm[i+1:].lstrip()
                if rest == "" or rest[0] in [',', '}', ']', ':']:
                    in_string = False
                    out.append(ch)
                else:
                    # Unescaped quote inside string! Escape it!
                    out.append('\\"')
            i += 1
            continue

        if in_string:
            if ch == '\n':
                out.append('\\n')
            elif ch == '\r':
                out.append('\\r')
            elif ch == '\t':
                out.append('\\t')
            else:
                out.append(ch)
        else:
            out.append(ch)
        i += 1

    result = "".join(out)
    result = re.sub(r",\s*([\]}])", r"\1", result)

    # Check balance using delimiter stack
    delim_stack = []
    in_str = False
    esc = False
    for c in result:
        if esc:
            esc = False
            continue
        if c == '\\':
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if not in_str:
            if c == '{':
                delim_stack.append('}')
            elif c == '[':
                delim_stack.append(']')
            elif c in ['}', ']']:
                if delim_stack and delim_stack[-1] == c:
                    delim_stack.pop()

    if in_str:
        result += '"'
    while delim_stack:
        result += delim_stack.pop()

    try:
        return json.loads(result, strict=False)
    except Exception as err:
        logger.warning(f"robust_json_loads failed: {err}. Raw input snippet: {text[:120]}")
        raise err
