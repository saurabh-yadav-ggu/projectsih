import json
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from langchain_ollama import ChatOllama
from app.config import settings
from app.repositories import MemoryRepository, ThreadRepository

logger = logging.getLogger("app.memory")

PROMPT_PATH = Path(__file__).resolve().parent / "prompt.json"

def get_prompts():
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
        lines.append(f"• {mem.memory_key.replace('_', ' ').title()}: {mem.memory_value}")
    lines.append("--- END USER MEMORIES ---\n")

    return "\n".join(lines)


def extract_and_save_memories(db: Session, user_id: int, user_message: str):
    """Background or inline non-blocking memory extraction."""
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
        content = response.content.strip()

        # Try to parse JSON array from output
        json_start = content.find("[")
        json_end = content.rfind("]") + 1
        if json_start != -1 and json_end > json_start:
            json_str = content[json_start:json_end]
            try:
                items = json.loads(json_str)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            key = item.get("key")
                            val = item.get("value")
                            if key and val:
                                key_str = str(key).strip()
                                val_str = str(val).strip()
                                if key_str and val_str:
                                    MemoryRepository.save_or_update_memory(db, user_id, key_str, val_str)
                                    logger.info(f"Extracted memory for user {user_id}: {key_str} = {val_str}")
            except Exception as parse_err:
                logger.debug(f"Could not parse memory extraction JSON: {parse_err}")

    except Exception as e:
        logger.warning(f"Memory extraction completed without new memories: {e}")


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
