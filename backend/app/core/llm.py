import logging
from typing import Optional, Any
from app.config import settings

logger = logging.getLogger("app.core.llm")


def get_llm(temperature: float = 0.1, model: Optional[str] = None) -> Any:
    """
    Unified LLM provider:
    - If USE_MISTRAL_API is True and MISTRAL_API_KEY is present, uses official Mistral AI API
      with ministral-3b-latest (or model override).
    - Otherwise, falls back gracefully to local sovereign Ollama.
    """
    if settings.USE_MISTRAL_API and settings.MISTRAL_API_KEY:
        try:
            from langchain_mistralai import ChatMistralAI
            target_model = model or settings.MISTRAL_MODEL
            return ChatMistralAI(
                model=target_model,
                api_key=settings.MISTRAL_API_KEY,
                temperature=temperature,
                max_tokens=4096,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize ChatMistralAI, falling back to ChatOllama: {e}")

    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=model or settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=temperature,
    )
