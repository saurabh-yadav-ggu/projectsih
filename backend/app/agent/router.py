import logging
import asyncio
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm import get_llm

logger = logging.getLogger("app.agent.router")

ROUTER_SYSTEM_PROMPT = """You are an expert AI task router for an enterprise sovereign assistant.
Your job is to analyze the user request and classify their primary intent into exactly ONE of the following 5 categories:

1. 'document': The user wants to CREATE, GENERATE, MAKE, DRAFT, BUILD, or EXPORT a new file or deliverable document (such as PDF, Word DOCX, Excel XLSX spreadsheet, PowerPoint PPTX presentation, CSV data table, or HTML file).
2. 'rag': The user wants to QUERY, SEARCH, EXPLAIN, SUMMARIZE, EXTRACT FROM, or ASK QUESTIONS ABOUT an uploaded or attached document, PDF, file, resume, or available document knowledge.
3. 'vision': The user attached an image, or specifically asks to inspect, analyze, describe, or extract text from a visual image, screenshot, photo, or diagram.
4. 'coding': The user wants to WRITE AND EXECUTE Python code or run a script in the sandbox.
5. 'chat': General conversation, greetings, standard questions, reasoning, math calculations, advice, or general Q&A that does not involve generating new files, interrogating uploaded docs, or running code.

Additional Context:
- Has Image Attached: {has_image}
- Has Uploaded Document Context: {has_document_context}

CRITICAL RULES:
- Greetings (e.g. 'hello', 'hi', 'hey', 'good morning', 'how are you'), small talk, chit-chat, and general advice MUST ALWAYS be classified as 'chat', NEVER 'rag'.
- Math calculations, arithmetic, formulas, and numeric questions (e.g. 'Can you calculate 25 * 40?', 'What is 15% of 80?') MUST ALWAYS be classified as 'chat' (the Chat agent has an integrated calculator tool). ONLY classify as 'coding' if the user explicitly asks to write or run a Python program/script/code.
- Generating or downloading new documents/spreadsheets/presentations/PDFs MUST ALWAYS be classified as 'document'.
- ONLY choose 'rag' if the user is explicitly asking about, querying, explaining, or summarizing an uploaded document/PDF/file, or asking a topic-specific question in a thread with uploaded document context.
- Output ONLY the single category name in lowercase (document, rag, vision, coding, chat). Do not output any explanation, markdown formatting, or punctuation.
"""

VALID_INTENTS = {"document", "rag", "vision", "coding", "chat"}


def _clean_intent(raw_output: str) -> str:
    cleaned = raw_output.strip().lower().strip("`'\".,!?:;\n ")
    for word in cleaned.split():
        if word in VALID_INTENTS:
            return word
    for intent in VALID_INTENTS:
        if intent in cleaned:
            return intent
    return "chat"


def _fallback_intent(query: str, has_image: bool, has_document_context: bool) -> str:
    q = query.lower().strip()
    if has_image:
        return "vision"
    if any(q.startswith(g) or q == g for g in ["hi", "hello", "hey", "good morning", "good evening", "how are you"]):
        return "chat"
    if any(k in q for k in ["run python", "write python", "execute code", "run script"]):
        return "coding"
    if any(k in q for k in ["create a", "generate a", "make a", "draft a", "export to", ".docx", ".xlsx", ".pptx", ".csv"]):
        return "document"
    if any(k in q for k in ["document", "pdf", "file", "uploaded", "attached", "resume", "explain this", "summarize"]):
        return "rag"
    if has_document_context and any(q.startswith(w) for w in ["what", "who", "where", "how", "why", "tell me about", "explain"]):
        return "rag"
    return "chat"


async def aroute_query_intent(query: str, has_image: bool = False, has_document_context: bool = False) -> str:
    """
    Asynchronously route user query using LLM intent classification.
    """
    try:
        llm = get_llm(temperature=0.0)
        prompt = ROUTER_SYSTEM_PROMPT.format(
            has_image=has_image,
            has_document_context=has_document_context
        )
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=query)
        ]
        response = await llm.ainvoke(messages)
        intent = _clean_intent(str(response.content))
        logger.info(f"LLM routed query '{query[:60]}...' to '{intent}'")
        return intent
    except Exception as e:
        logger.warning(f"LLM router ainvoke failed: {e}. Using fallback.")
        return _fallback_intent(query, has_image, has_document_context)


def route_query_intent(query: str, has_image: bool = False, has_document_context: bool = False) -> str:
    """
    Synchronously route user query using LLM intent classification (with fallback).
    """
    try:
        # Check if already inside an active asyncio event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If inside running loop, invoke synchronously in worker thread to prevent event loop collision
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                def _call_sync():
                    llm = get_llm(temperature=0.0)
                    prompt = ROUTER_SYSTEM_PROMPT.format(
                        has_image=has_image,
                        has_document_context=has_document_context
                    )
                    messages = [
                        SystemMessage(content=prompt),
                        HumanMessage(content=query)
                    ]
                    res = llm.invoke(messages)
                    return _clean_intent(str(res.content))
                future = executor.submit(_call_sync)
                return future.result(timeout=15)
        else:
            llm = get_llm(temperature=0.0)
            prompt = ROUTER_SYSTEM_PROMPT.format(
                has_image=has_image,
                has_document_context=has_document_context
            )
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=query)
            ]
            response = llm.invoke(messages)
            return _clean_intent(str(response.content))
    except Exception as e:
        logger.warning(f"LLM router invoke failed: {e}. Using fallback.")
        return _fallback_intent(query, has_image, has_document_context)
