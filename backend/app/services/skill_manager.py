import os
import re
import time
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("app.services.skill_manager")

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
CUSTOM_SKILLS_DIR = SKILLS_DIR / "custom"
INSTALLED_SKILLS_DIR = SKILLS_DIR / "installed"
DOCUMENT_PROCESSING_DIR = INSTALLED_SKILLS_DIR / "document-processing"

CUSTOM_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
INSTALLED_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENT_PROCESSING_DIR.mkdir(parents=True, exist_ok=True)


def parse_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    """Extracts simple YAML frontmatter and remaining markdown content."""
    meta = {}
    content = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            content = parts[2].strip()
            for line in fm_text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip().strip('"\'')
                    meta[key] = val
    return meta, content


class SkillManager:
    """
    Central registry and discovery engine prioritizing:
    1. Main Document Processing Skills (skills/installed/document-processing: docx-official, pdf-processing-pro, xlsx, pptx-official, documentation-templates)
    2. User-created Custom Skills (skills/custom)
    3. Other Installed Templates (ai-maestro, scientific, creative-design)
    4. Core System Skills (coding, rag, vision, verification)
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or SKILLS_DIR
        self.custom_dir = self.base_dir / "custom"
        self.installed_dir = self.base_dir / "installed"
        self.doc_processing_dir = self.installed_dir / "document-processing"
        self.custom_dir.mkdir(parents=True, exist_ok=True)

    def _format_skill_entry(self, skill_path: Path, is_system: bool = True) -> Dict[str, Any]:
        content_text = ""
        try:
            content_text = skill_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Failed to read skill at {skill_path}: {e}")

        meta, body = parse_frontmatter(content_text)
        
        # Calculate skill ID relative to base_dir
        try:
            rel_path = skill_path.parent.relative_to(self.base_dir).as_posix()
        except ValueError:
            rel_path = skill_path.parent.name

        name = meta.get("name") or skill_path.parent.name
        title = meta.get("title") or meta.get("display_name") or name.replace("-", " ").replace("_", " ").title()
        description = meta.get("description") or ""

        # If description is missing, extract first line or header
        if not description:
            for line in body.splitlines():
                clean_l = line.strip().lstrip("#").strip()
                if clean_l and not clean_l.startswith("---"):
                    description = clean_l[:180]
                    break

        category = meta.get("category")
        if not category:
            if "document" in rel_path or "documents" in rel_path:
                category = "document"
            elif "coding" in rel_path:
                category = "coding"
            elif "ai-maestro" in rel_path:
                category = "ai-system"
            elif "scientific" in rel_path:
                category = "scientific"
            elif "creative" in rel_path:
                category = "design"
            elif not is_system:
                category = "custom"
            else:
                category = "general"

        doc_format = meta.get("format")
        if not doc_format:
            name_lower = name.lower()
            if "pdf" in name_lower or "pdf" in rel_path:
                doc_format = "pdf"
            elif "docx" in name_lower or "docx" in rel_path or "word" in name_lower:
                doc_format = "docx"
            elif "xlsx" in name_lower or "xlsx" in rel_path or "excel" in name_lower:
                doc_format = "xlsx"
            elif "pptx" in name_lower or "pptx" in rel_path or "powerpoint" in name_lower:
                doc_format = "pptx"
            elif "html" in name_lower:
                doc_format = "html"
            elif "csv" in name_lower:
                doc_format = "csv"
            elif "coding" in name_lower or "python" in name_lower:
                doc_format = "python"
            else:
                doc_format = "text"

        mtime = os.path.getmtime(skill_path) if skill_path.exists() else time.time()

        return {
            "id": rel_path,
            "name": name,
            "title": title,
            "description": description,
            "category": category,
            "format": doc_format,
            "is_system": is_system,
            "path": skill_path.as_posix(),
            "updated_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
            "content": content_text,
        }

    def list_skills(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns metadata for all available skills."""
        results = []
        seen_ids = set()

        # 1. Custom User Skills
        if self.custom_dir.exists():
            for skill_file in sorted(self.custom_dir.glob("**/SKILL.md")):
                entry = self._format_skill_entry(skill_file, is_system=False)
                if entry["id"] not in seen_ids:
                    results.append(entry)
                    seen_ids.add(entry["id"])

        # 2. Installed Templates (from claude-code-templates)
        if self.installed_dir.exists():
            for skill_file in sorted(self.installed_dir.glob("**/SKILL.md")):
                entry = self._format_skill_entry(skill_file, is_system=True)
                if entry["id"] not in seen_ids:
                    results.append(entry)
                    seen_ids.add(entry["id"])

        # 3. Built-in Core Skills
        for skill_file in sorted(self.base_dir.glob("**/SKILL.md")):
            # Skip if inside custom or installed (already processed)
            if "custom" in skill_file.parts or "installed" in skill_file.parts:
                continue
            entry = self._format_skill_entry(skill_file, is_system=True)
            if entry["id"] not in seen_ids:
                results.append(entry)
                seen_ids.add(entry["id"])

        if category:
            results = [s for s in results if s["category"].lower() == category.lower()]

        return results

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Fetch complete skill details including full markdown by ID or name."""
        all_skills = self.list_skills()
        for s in all_skills:
            if s["id"] == skill_id or s["name"] == skill_id or s["id"].endswith(skill_id):
                return s
        return None

    def create_custom_skill(
        self,
        name: str,
        title: str,
        description: str,
        category: str = "custom",
        doc_format: str = "text",
        content: str = "",
    ) -> Dict[str, Any]:
        """Creates a new user skill and writes SKILL.md with frontmatter."""
        clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name.strip().lower()).strip("_")
        if not clean_name:
            clean_name = f"custom_skill_{int(time.time())}"

        skill_dir = self.custom_dir / clean_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"

        frontmatter = (
            f"---\n"
            f"name: {clean_name}\n"
            f"title: {title or clean_name.title()}\n"
            f"description: {description}\n"
            f"category: {category or 'custom'}\n"
            f"format: {doc_format or 'text'}\n"
            f"---\n\n"
        )
        full_text = frontmatter + (content.strip() or f"# {title}\n\n{description}\n")
        skill_file.write_text(full_text, encoding="utf-8")

        return self._format_skill_entry(skill_file, is_system=False)

    def update_custom_skill(
        self,
        skill_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        doc_format: Optional[str] = None,
        content: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Updates an existing custom skill."""
        existing = self.get_skill(skill_id)
        if not existing or existing.get("is_system"):
            return None

        skill_path = Path(existing["path"])
        if not skill_path.exists():
            return None

        current_meta, current_body = parse_frontmatter(existing["content"])
        
        new_title = title if title is not None else current_meta.get("title", existing["title"])
        new_desc = description if description is not None else current_meta.get("description", existing["description"])
        new_cat = category if category is not None else current_meta.get("category", existing["category"])
        new_fmt = doc_format if doc_format is not None else current_meta.get("format", existing["format"])
        new_body = content if content is not None else current_body

        frontmatter = (
            f"---\n"
            f"name: {existing['name']}\n"
            f"title: {new_title}\n"
            f"description: {new_desc}\n"
            f"category: {new_cat}\n"
            f"format: {new_fmt}\n"
            f"---\n\n"
        )
        skill_path.write_text(frontmatter + new_body.strip(), encoding="utf-8")
        return self._format_skill_entry(skill_path, is_system=False)

    def delete_custom_skill(self, skill_id: str) -> bool:
        """Deletes a user-created skill folder."""
        existing = self.get_skill(skill_id)
        if not existing or existing.get("is_system"):
            return False

        skill_path = Path(existing["path"])
        parent_dir = skill_path.parent
        try:
            if parent_dir.exists() and parent_dir.is_relative_to(self.custom_dir):
                shutil.rmtree(parent_dir)
                return True
        except Exception as e:
            logger.error(f"Failed to delete custom skill at {parent_dir}: {e}")
        return False

    def match_skill(self, query: str, format_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Dynamically matches a user query to the most relevant skill file.
        Returns:
            {
                "skill": skill_dict or None,
                "content": str,
                "format": str (e.g. 'pdf', 'docx', 'xlsx', 'pptx')
            }
        """
        q = query.lower()
        all_skills = self.list_skills()

        # 1. Check custom skills first (user overrides)
        for s in all_skills:
            if not s["is_system"]:
                s_name = s["name"].lower()
                s_title = s["title"].lower()
                if s_name in q or s_title in q or any(word in q for word in s_name.split("_") if len(word) > 3):
                    return {
                        "skill": s,
                        "content": s["content"],
                        "format": s["format"] or format_hint or "docx",
                    }

        # 2. Check for explicit format requirements
        target_fmt = format_hint
        if not target_fmt:
            if any(term in q for term in ["pdf", ".pdf", "pdf document", "as a pdf", "in pdf"]):
                target_fmt = "pdf"
            elif any(term in q for term in ["xlsx", ".xlsx", "excel", "spreadsheet", "sheet", "csv"]):
                target_fmt = "xlsx" if "csv" not in q else "csv"
            elif any(term in q for term in ["pptx", ".pptx", "powerpoint", "presentation", "slides", "deck"]):
                target_fmt = "pptx"
            elif any(term in q for term in ["docx", ".docx", "word", "document", "report"]):
                target_fmt = "docx"
            elif any(term in q for term in ["html", ".html", "webpage", "web page"]):
                target_fmt = "html"

        # 3. Find matching skill in installed/document-processing main skills
        if target_fmt:
            format_to_skill = {
                "docx": ["docx-official", "docx"],
                "pdf": ["pdf-processing-pro", "pdf"],
                "xlsx": ["xlsx", "excel"],
                "csv": ["xlsx", "csv"],
                "pptx": ["pptx-official", "pptx"],
                "html": ["documentation-templates", "html"],
            }
            preferred_keys = format_to_skill.get(target_fmt.lower(), [target_fmt.lower()])

            # Priority 1: Match directly from installed/document-processing main skills
            for key in preferred_keys:
                for s in all_skills:
                    if "document-processing" in s["id"] and (key in s["name"].lower() or key in s["id"].lower()):
                        return {
                            "skill": s,
                            "content": s["content"],
                            "format": target_fmt,
                        }

            # Priority 2: Match by format across other skills
            for s in all_skills:
                if s["format"].lower() == target_fmt.lower():
                    return {
                        "skill": s,
                        "content": s["content"],
                        "format": target_fmt,
                    }

        # 4. Keyword search across descriptions
        for s in all_skills:
            words = [w for w in s["name"].lower().replace("-", " ").split() if len(w) > 3]
            if any(w in q for w in words):
                return {
                    "skill": s,
                    "content": s["content"],
                    "format": s["format"] or "docx",
                }

        # 5. Default Fallback -> dynamically select skill matching target_fmt
        default_skill = None
        if target_fmt:
            fmt_lower = target_fmt.lower().lstrip(".")
            for s in all_skills:
                if s.get("format", "").lower() == fmt_lower:
                    default_skill = s
                    break
        if not default_skill:
            default_skill = (
                self.get_skill("installed/document-processing/docx-official")
                or self.get_skill("docx-official")
                or self.get_skill("pdf-processing-pro")
            )
        default_content = default_skill["content"] if default_skill else (
            "Generate a professional document with clear structure, metadata, and clean styling."
        )
        return {
            "skill": default_skill,
            "content": default_content,
            "format": target_fmt or (default_skill.get("format") if default_skill else "docx"),
        }


# Global singleton instance
skill_manager = SkillManager()
