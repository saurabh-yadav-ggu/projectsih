import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("app.agent.document_workflow.discovery")

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "skills"


class DynamicSkillDiscovery:
    """
    Dynamically discovers and loads relevant skills based on user intent and format.
    Reads SKILL.md metadata and instructions without hardcoded assumptions.
    """

    @classmethod
    def discover_skills(cls, query: str, doc_format: str) -> List[Dict[str, Any]]:
        matched_skills = []
        fmt = doc_format.lower().lstrip(".")

        search_roots = [
            SKILLS_DIR / "installed" / "document-processing",
            SKILLS_DIR / "installed",
            SKILLS_DIR / "documents",
            SKILLS_DIR,
        ]

        # Scan for relevant SKILL.md files
        seen_paths = set()
        for root in search_roots:
            if not root.exists():
                continue
            for skill_file in root.glob("**/SKILL.md"):
                if skill_file in seen_paths:
                    continue
                seen_paths.add(skill_file)

                try:
                    text = skill_file.read_text(encoding="utf-8", errors="ignore")
                    skill_name = skill_file.parent.name
                    # Parse YAML frontmatter name if present
                    fm_match = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
                    if fm_match:
                        name_match = re.search(r"name:\s*([^\n]+)", fm_match.group(1))
                        if name_match:
                            skill_name = name_match.group(1).strip()

                    # Relevance check against format or query
                    is_format_match = (
                        (fmt in ["docx", "doc"] and any(k in text.lower() for k in ["docx", "word", "document-processing"])) or
                        (fmt in ["xlsx", "xls", "csv"] and any(k in text.lower() for k in ["xlsx", "excel", "spreadsheet"])) or
                        (fmt in ["pptx", "ppt"] and any(k in text.lower() for k in ["pptx", "powerpoint", "presentation", "slides"])) or
                        (fmt == "pdf" and any(k in text.lower() for k in ["pdf", "reportlab"]))
                    )

                    is_query_match = any(w.lower() in text.lower() for w in query.split() if len(w) > 4)

                    if is_format_match or is_query_match:
                        matched_skills.append({
                            "name": skill_name,
                            "path": str(skill_file),
                            "format": fmt,
                            "instructions": text[:2000],  # Concise instruction extract
                        })
                except Exception as e:
                    logger.debug(f"Failed parsing skill at {skill_file}: {e}")

        # Fallback default if no installed skills located
        if not matched_skills:
            matched_skills.append({
                "name": f"{fmt.upper()} Processing Skill",
                "path": "builtin",
                "format": fmt,
                "instructions": f"Standard {fmt.upper()} document generation skill.",
            })

        logger.info(f"Discovered {len(matched_skills)} relevant skill(s) for format '{fmt}'.")
        return matched_skills
