import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.core.llm import get_llm
from app.repositories import MemoryRepository, ThreadRepository

logger = logging.getLogger("app.memory")

PROMPT_PATH = Path(__file__).resolve().parent / "prompt.json"


def get_prompts() -> Dict[str, str]:
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading prompt.json: {e}")
        return {
            "system_prompt": "You are ShieldAi assistant.",
            "title_generation_prompt": "Generate a short title for: {message}",
            "memory_extraction_prompt": "Extract memory from: {message}"
        }


def format_memories_for_prompt(db: Session, user_id: int) -> str:
    """Format user memories into a text block for agent context."""
    memories = MemoryRepository.get_user_memories(db, user_id)
    if not memories:
        return ""

    lines = ["\n--- USER LONG-TERM MEMORIES ---"]
    for mem in memories:
        key_fmt = mem.memory_key.replace("_", " ").title()
        lines.append(f"• {key_fmt}: {mem.memory_value}")
    lines.append("--- END USER MEMORIES ---\n")

    return "\n".join(lines)


def _clean_json_response(content: str) -> str:
    """Strip markdown codeblock wrappers and sanitize JSON string."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        # Remove opening ```json or ```
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        # Remove closing ```
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def extract_and_save_memories(
    arg1: Any = None,
    arg2: Any = None,
    arg3: Any = None,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    user_message: Optional[str] = None
):
    """Background or inline non-blocking memory extraction with resilient JSON parsing."""
    if isinstance(arg1, Session):
        db = arg1
        user_id = arg2
        user_message = arg3
    elif isinstance(arg1, int):
        user_id = arg1
        user_message = arg2
        if isinstance(arg3, Session):
            db = arg3

    if not user_id or not user_message:
        return

    close_db = False
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
        close_db = True

    try:
        prompts = get_prompts()
        prompt_tmpl = prompts.get("memory_extraction_prompt", "")
        # Use replace instead of .format to avoid KeyError with unescaped JSON braces in prompt
        prompt = prompt_tmpl.replace("{message}", str(user_message))

        llm = get_llm(temperature=0)

        response = llm.invoke(prompt)
        raw_content = response.content.strip()
        cleaned_content = _clean_json_response(raw_content)

        if not cleaned_content or cleaned_content in ["[]", "{}"]:
            logger.debug(f"No long-term memories extracted for user {user_id}.")
            return

        parsed_data = None
        # Attempt standard JSON parse
        try:
            parsed_data = json.loads(cleaned_content)
        except json.JSONDecodeError:
            # Fallback: extract array or object via regex if surrounded by text
            arr_match = re.search(r"\[.*\]", cleaned_content, re.DOTALL)
            obj_match = re.search(r"\{.*\}", cleaned_content, re.DOTALL)
            if arr_match:
                try:
                    parsed_data = json.loads(arr_match.group(0))
                except Exception:
                    pass
            elif obj_match:
                try:
                    parsed_data = json.loads(obj_match.group(0))
                except Exception:
                    pass

        if parsed_data is None:
            logger.debug(f"Memory extraction output could not be parsed into JSON for user {user_id}.")
            return

        # Normalize to list of dicts with key/value
        items_to_process: List[Dict[str, Any]] = []

        if isinstance(parsed_data, list):
            for elem in parsed_data:
                if isinstance(elem, dict):
                    if "key" in elem and "value" in elem:
                        items_to_process.append(elem)
                    else:
                        for k, v in elem.items():
                            items_to_process.append({"key": k, "value": v})
        elif isinstance(parsed_data, dict):
            if "key" in parsed_data and "value" in parsed_data:
                items_to_process.append(parsed_data)
            else:
                for k, v in parsed_data.items():
                    items_to_process.append({"key": k, "value": v})

        saved_count = 0
        invalid_keys = {"key", "keys", "memory", "none", "null", "n/a", "undefined", "item"}
        invalid_vals = {"value", "values", "none", "null", "n/a", "undefined", ""}

        for item in items_to_process:
            key_raw = str(item.get("key", "")).strip().lower()
            val_raw = str(item.get("value", "")).strip()

            if not key_raw or not val_raw:
                continue
            if key_raw in invalid_keys or val_raw.lower() in invalid_vals:
                continue

            MemoryRepository.save_or_update_memory(
                db=db,
                user_id=user_id,
                memory_key=key_raw,
                memory_value=val_raw
            )
            saved_count += 1
            logger.info(f"Saved long-term memory for user {user_id}: '{key_raw}' = '{val_raw}'")

        if saved_count == 0:
            logger.debug(f"Memory extraction ran successfully for user {user_id}; no durable memories saved.")

    except Exception as e:
        logger.error(f"Memory extraction error for user {user_id}: {e}", exc_info=True)
    finally:
        if close_db and db is not None:
            try:
                db.close()
            except Exception:
                pass


def generate_and_save_title(
    arg1: Any = None,
    arg2: Any = None,
    arg3: Any = None,
    arg4: Any = None,
    db: Optional[Session] = None,
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None,
    user_message: Optional[str] = None
):
    """Generate title for new thread automatically based on initial user message."""
    if isinstance(arg1, Session):
        db = arg1
        thread_id = arg2
        user_id = arg3
        user_message = arg4
    elif isinstance(arg1, str):
        thread_id = arg1
        user_id = arg2
        user_message = arg3
        if isinstance(arg4, Session):
            db = arg4

    if not thread_id or not user_id or not user_message:
        return

    close_db = False
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
        close_db = True

    try:
        thread = ThreadRepository.get_thread(db, thread_id, user_id)
        if not thread or thread.title != "New conversation":
            return

        prompts = get_prompts()
        prompt_tmpl = prompts.get("title_generation_prompt", "")
        prompt = prompt_tmpl.replace("{message}", str(user_message))

        llm = get_llm(temperature=0.3)

        response = llm.invoke(prompt)
        title = response.content.strip().strip('"').strip("'")
        if len(title) > 60:
            title = title[:57] + "..."

        if title:
            ThreadRepository.update_title(db, thread_id, user_id, title)
            logger.info(f"Generated title for thread {thread_id}: {title}")

    except Exception as e:
        logger.warning(f"Title generation failed: {e}")
    finally:
        if close_db and db is not None:
            try:
                db.close()
            except Exception:
                pass
