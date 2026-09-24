import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger("app.agent.document_workflow.repair")


class TargetedRepairManager:
    """
    Manages surgical repair of failed sections.
    If semantic validation fails on section 3, only section 3 is repaired and regenerated.
    Enforces a strict repair limit to guarantee termination.
    """

    def __init__(self, max_repairs: int = 2):
        self.max_repairs = max_repairs
        self.repair_history: List[Dict[str, Any]] = []

    def can_repair(self, current_repairs: int) -> bool:
        return current_repairs < self.max_repairs

    @staticmethod
    def identify_failed_section_indices(validation_issues: List[Dict[str, Any]], sections: List[Dict[str, Any]]) -> List[int]:
        """Finds section indices that contain validation errors."""
        failed_indices = set()
        for issue in validation_issues:
            if not isinstance(issue, dict):
                continue
            sec_id = issue.get("section_id", "")
            # Match section_1, section_2, etc.
            match = re.search(r"section_(\d+)", sec_id)
            if match:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(sections):
                    failed_indices.add(idx)
            else:
                # If specific section name is mentioned
                msg = issue.get("message", "").lower()
                for i, sec in enumerate(sections):
                    if isinstance(sec, dict):
                        h = sec.get("heading", "").lower()
                    elif isinstance(sec, str):
                        h = sec.lower()
                    else:
                        h = ""
                    if h and h in msg:
                        failed_indices.add(i)

        return sorted(list(failed_indices))

    def repair_section_content(
        self,
        section: Dict[str, Any],
        issues: List[Dict[str, Any]],
        scope_lock: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Surgically scrubs placeholders or forbidden content from a single section."""
        if isinstance(section, str):
            section = {"heading": section, "paragraphs": [f"Details for {section}."]}
        elif not isinstance(section, dict):
            section = {"heading": "Section", "paragraphs": [str(section)]}

        if not isinstance(scope_lock, dict):
            scope_lock = {"must_not_include": []}

        repaired = dict(section)
        heading = section.get("heading", "")
        paras = list(section.get("paragraphs", []))
        bullets = list(section.get("bullet_points", []))

        must_not_include = scope_lock.get("must_not_include", [])

        # Clean paragraphs
        cleaned_paras = []
        for p in paras:
            cp = re.sub(r"\[insert[^\]]*\]|lorem ipsum|\btodo\b.*|\btbd\b.*|<placeholder>", "", p, flags=re.IGNORECASE)
            for forbidden in must_not_include:
                if forbidden.lower() in cp.lower():
                    # Remove the forbidden phrase/sentence
                    cp = re.sub(re.escape(forbidden), "", cp, flags=re.IGNORECASE)
            cp = re.sub(r"\s+", " ", cp).strip(" :,-.")
            if cp:
                cleaned_paras.append(cp)

        # Clean bullets
        cleaned_bullets = []
        for b in bullets:
            cb = re.sub(r"\[insert[^\]]*\]|lorem ipsum|\btodo\b.*|\btbd\b.*|<placeholder>", "", b, flags=re.IGNORECASE)
            for forbidden in must_not_include:
                if forbidden.lower() in cb.lower():
                    cb = re.sub(re.escape(forbidden), "", cb, flags=re.IGNORECASE)
            cb = re.sub(r"\s+", " ", cb).strip(" :,-.")
            if cb:
                cleaned_bullets.append(cb)

        repaired["paragraphs"] = cleaned_paras or ["Information unavailable from provided sources."]
        repaired["bullet_points"] = cleaned_bullets

        record = {
            "section_heading": heading,
            "issues_addressed": len(issues),
            "status": "REPAIRED",
        }
        self.repair_history.append(record)
        logger.info(f"Targeted repair applied to section '{heading}'.")
        return repaired
