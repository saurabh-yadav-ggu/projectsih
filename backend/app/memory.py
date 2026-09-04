import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from langchain_ollama import ChatOllama
from app.config import settings
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


def extract_and_save_memories(db: Session, user_id: int, user_message: str):
    """Background or inline non-blocking memory extraction with resilient JSON parsing."""
    try:
        prompts = get_prompts()
        prompt_tmpl = prompts.get("memory_extraction_prompt", "")
        prompt = prompt_tmpl.format(message=user_message)

        llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0
        )

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
                        # Dict mapping keys directly to values (e.g. {"user_role": "Engineer"})
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
        logger.debug(f"Memory extraction process completed without updates: {e}")


def generate_and_save_title(db: Session, thread_id: str, user_id: int, user_message: str):
    """Generate title for new thread automatically based on initial user message."""
    try:
        thread = ThreadRepository.get_thread(db, thread_id, user_id)
        if not thread or thread.title != "New conversation":
            return

        prompts = get_prompts()
        prompt_tmpl = prompts.get("title_generation_prompt", "")
        prompt = prompt_tmpl.format(message=user_message)

        llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.3
        )

        response = llm.invoke(prompt)
        title = response.content.strip().strip('"').strip("'")
        if len(title) > 60:
            title = title[:57] + "..."

        if title:
            ThreadRepository.update_title(db, thread_id, user_id, title)
            logger.info(f"Generated title for thread {thread_id}: {title}")

    except Exception as e:
        logger.warning(f"Title generation failed: {e}")
