import json
import logging
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from app.config import settings
from app.core.llm import get_llm
from app.core.json_utils import robust_json_loads
from app.agent.prompts import PLANNER_PROMPT
from app.agent.router import aroute_query_intent, route_query_intent

logger = logging.getLogger("app.agent.planner")


def _detect_format_from_query(query: str) -> str:
    q = query.lower()
    if any(k in q for k in [".xlsx", "xlsx", "excel", "spreadsheet", "sheets"]):
        return "xlsx"
    if any(k in q for k in [".pptx", "pptx", "powerpoint", "presentation", "slides"]):
        return "pptx"
    if any(k in q for k in [".pdf", "pdf"]):
        return "pdf"
    if any(k in q for k in [".csv", "csv"]):
        return "csv"
    if any(k in q for k in [".html", "html", "webpage"]):
        return "html"
    return "docx"


async def generate_execution_plan(
    query: str,
    has_image: bool = False,
    has_doc_context: bool = False
) -> Dict[str, Any]:
    """
    Generates a structured execution plan identifying target intent, subagents, and steps.
    """
    intent = await aroute_query_intent(query, has_image=has_image, has_document_context=has_doc_context)

    # Simple chat queries don't need heavyweight LLM planning
    if intent == "chat":
        return {
            "intent": "chat",
            "steps": ["Direct conversational processing via ChatAgent"],
            "target_format": None,
            "rationale": "Standard conversational query.",
        }

    # For document, RAG, or coding tasks, generate explicit plan
    try:
        llm = get_llm(temperature=0)
        prompt = f"{PLANNER_PROMPT}\n\nUser Request: {query}"
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = str(response.content).strip()

        # Parse JSON from response
        try:
            plan = robust_json_loads(content)
        except Exception:
            if "{" in content and "}" in content:
                json_str = content[content.find("{"):content.rfind("}") + 1]
                plan = json.loads(json_str, strict=False)
            else:
                raise
        if not isinstance(plan, dict):
            plan = {"intent": intent, "steps": [str(plan)]}
            # Never downgrade specialized intent (like document) to generic chat
            if intent in ["document", "rag", "vision", "coding"]:
                plan["intent"] = intent
            else:
                plan["intent"] = plan.get("intent") or intent

            if intent == "document" and not plan.get("target_format"):
                plan["target_format"] = _detect_format_from_query(query)
            return plan
    except Exception as e:
        logger.warning(f"Planner LLM failed, using fallback plan: {e}")

    # Fallback heuristic plan
    return {
        "intent": intent,
        "steps": [
            f"Route request to {intent.title()} Agent",
            "Execute task using appropriate skills and sandbox",
            "Verify outputs and compile response"
        ],
        "target_format": _detect_format_from_query(query) if intent == "document" else None,
        "rationale": f"Rule-based plan for {intent} intent.",
    }
