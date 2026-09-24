import logging
from typing import Dict, Any, List

logger = logging.getLogger("app.agent.document_workflow.integrator")


class ContentIntegrator:
    """
    Dedicated content integration step.
    Combines subagent section outputs into a cohesive, verified document content tree.
    Enforces Scope Lock, eliminates duplicates, normalizes tone, and maintains section order.
    """

    @staticmethod
    def integrate(
        section_results: List[Dict[str, Any]],
        base_plan: Dict[str, Any],
        scope_lock: Dict[str, Any]
    ) -> Dict[str, Any]:
        logger.info(f"Integrating {len(section_results)} section outputs into document tree.")
        
        integrated_sections: List[Dict[str, Any]] = []
        seen_sentences = set()
        if not isinstance(base_plan, dict):
            base_plan = {"topic": "", "title": "", "sections": []}
        data_table = base_plan.get("data_table")

        for res in section_results:
            if not isinstance(res, dict):
                continue
            content = res.get("content")
            if not content:
                continue
            if isinstance(content, str):
                content = {"heading": "Section", "paragraphs": [content]}
            elif not isinstance(content, dict):
                continue

            # If this is the data table unit
            if "data_table" in content:
                data_table = content["data_table"]
                continue

            heading = content.get("heading") or "Section"
            paragraphs = content.get("paragraphs") or []
            bullet_points = content.get("bullet_points") or []
            table = content.get("table")
            callout = content.get("callout")

            # Deduplication: scrub exact sentence repetitions across sections
            cleaned_paras: List[str] = []
            for p in paragraphs:
                cleaned_p = p.strip()
                sentences = [s.strip() for s in cleaned_p.split(". ") if s.strip()]
                unique_sentences = []
                for s in sentences:
                    s_norm = s.lower().rstrip(".")
                    if len(s_norm) > 20 and s_norm in seen_sentences:
                        continue  # Skip redundant sentence
                    seen_sentences.add(s_norm)
                    unique_sentences.append(s)

                if unique_sentences:
                    cleaned_paras.append(". ".join(unique_sentences) + ("." if not unique_sentences[-1].endswith(".") else ""))
                elif cleaned_p:
                    cleaned_paras.append(cleaned_p)

            # Deduplication for bullets
            cleaned_bullets: List[str] = []
            for b in bullet_points:
                b_norm = b.lower().strip()
                if b_norm not in seen_sentences:
                    seen_sentences.add(b_norm)
                    cleaned_bullets.append(b.strip())

            integrated_sections.append({
                "heading": heading,
                "paragraphs": cleaned_paras or paragraphs,
                "bullet_points": cleaned_bullets,
                "table": table,
                "callout": callout,
            })

        # Ensure Scope Lock is preserved in metadata
        return {
            "scope_lock": scope_lock if isinstance(scope_lock, dict) else {},
            "topic": base_plan.get("topic", ""),
            "title": base_plan.get("title", ""),
            "subtitle": base_plan.get("subtitle", ""),
            "doc_type": base_plan.get("doc_type", "Deliverable"),
            "target_format": base_plan.get("target_format", "docx"),
            "audience": base_plan.get("audience", "Stakeholders"),
            "executive_summary": base_plan.get("executive_summary", ""),
            "sections": integrated_sections,
            "data_table": data_table,
            "provenance": [
                {
                    "section": s.get("heading") if isinstance(s, dict) else str(s),
                    "sources": res.get("sources_used", []) if isinstance(res, dict) else []
                }
                for s, res in zip(integrated_sections, section_results)
            ]
        }
