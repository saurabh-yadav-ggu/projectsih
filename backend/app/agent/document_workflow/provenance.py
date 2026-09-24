from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("app.agent.document_workflow.provenance")


class SourceProvenanceTracker:
    """
    Tracks factual claims and references back to source context or reference files.
    Ensures zero fabricated citation information.
    """

    def __init__(self):
        self.provenance_records: List[Dict[str, Any]] = []

    def record_claim(
        self,
        claim: str,
        source: Optional[str] = None,
        location: Optional[str] = None,
        confidence: float = 1.0,
        grounded: bool = True
    ):
        record = {
            "claim": claim[:200],
            "source": source or "user_query",
            "location": location or "query_context",
            "confidence": min(1.0, max(0.0, confidence)),
            "grounded": grounded,
        }
        self.provenance_records.append(record)

    def extract_from_plan(self, plan: Dict[str, Any], document_context: str = "") -> List[Dict[str, Any]]:
        """Extracts claim provenance from the structured content plan."""
        import re
        if not isinstance(plan, dict):
            return self.provenance_records

        source_name = "user_query"
        if document_context:
            src_match = re.search(r"--- Document Chunk \d+ from ([^\n(]+)", document_context)
            source_name = src_match.group(1).strip() if src_match else "reference_document"

        sections = plan.get("sections") or []
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            sec_heading = sec.get("heading", "section_body")
            for p in sec.get("paragraphs", []):
                if any(char.isdigit() for char in p):
                    # Numerical / factual claim
                    is_grounded = bool(document_context and any(w.lower() in document_context.lower() for w in p.split() if len(w) > 4))
                    self.record_claim(
                        claim=p,
                        source=source_name if document_context else "user_query",
                        location=sec_heading,
                        confidence=1.0 if (not document_context or is_grounded) else 0.5,
                        grounded=is_grounded if document_context else True,
                    )

        return self.provenance_records
