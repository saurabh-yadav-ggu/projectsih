import json
import logging
import re
from enum import Enum
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.llm import get_llm

logger = logging.getLogger("app.agent.document_workflow.complexity")


class ComplexityLevel(str, Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


class ComplexityDecision(BaseModel):
    level: ComplexityLevel = Field(
        ...,
        description="Complexity classification: SMALL, MEDIUM, or LARGE"
    )
    estimated_sections: int = Field(
        1,
        ge=1,
        description="Estimated number of sections if not explicitly defined in the plan"
    )
    use_async_subagents: bool = Field(
        False,
        description="Whether parallel async subagents should be spawned"
    )
    rationale: str = Field(
        ...,
        description="Concise rationale for the complexity decision"
    )


COMPLEXITY_SYSTEM_PROMPT = """You are an intelligent task complexity evaluator for an autonomous document generation system.
Analyze the user request, target format, document plan (if provided), and reference document context.

Evaluate the structural and cognitive scope required to author the document:
- SMALL: Straightforward, single-focus, or concise document (typically 1-2 sections). Can be created directly by the Primary Agent without delegating to sub-agents (use_async_subagents: false).
- MEDIUM: Standard deliverable with moderate scope and depth (typically 2-3 sections). Decomposed for structured section authoring.
- LARGE: High-complexity, multi-part, comprehensive, or exhaustive deliverable (typically 4+ sections or deep domain elaboration). Requires decomposition into parallel async section sub-agents (use_async_subagents: true).

Output your decision strictly as a JSON object adhering to this schema:
{
  "level": "SMALL" | "MEDIUM" | "LARGE",
  "estimated_sections": <integer >= 1>,
  "use_async_subagents": <boolean>,
  "rationale": "<concise explanation of why this complexity level and subagent strategy was chosen>"
}
"""


def _format_user_prompt(
    query: str,
    doc_format: str,
    doc_plan: Optional[Any] = None,
    document_context: str = ""
) -> str:
    sections_info = "None provided"
    if isinstance(doc_plan, dict):
        raw_sections = doc_plan.get("sections")
        if isinstance(raw_sections, list):
            sec_names = []
            for s in raw_sections:
                if isinstance(s, dict) and s.get("heading"):
                    sec_names.append(s["heading"])
                elif isinstance(s, str):
                    sec_names.append(s)
            sections_info = f"{len(raw_sections)} section(s): {', '.join(sec_names[:6])}"
            if len(sec_names) > 6:
                sections_info += f" (+{len(sec_names) - 6} more)"
        plan_desc = f"Title: {doc_plan.get('title', 'N/A')}, Topic: {doc_plan.get('topic', 'N/A')}, Sections: {sections_info}"
    elif doc_plan:
        plan_desc = str(doc_plan)[:400]
    else:
        plan_desc = "None provided"

    context_info = f"{len(document_context)} characters available" if document_context else "None"
    if document_context:
        context_preview = document_context[:600].strip()
    else:
        context_preview = "N/A"

    return (
        f"User Query: {query}\n"
        f"Target Document Format: {doc_format}\n"
        f"Document Plan: {plan_desc}\n"
        f"Reference Context: {context_info} (Preview: {context_preview})\n\n"
        f"Determine the complexity tier (SMALL, MEDIUM, or LARGE), estimated sections, and whether to use async subagents."
    )


def _parse_llm_decision(raw_output: Any) -> ComplexityDecision:
    if isinstance(raw_output, ComplexityDecision):
        return raw_output
    if isinstance(raw_output, dict):
        return ComplexityDecision.model_validate(raw_output)

    text = raw_output.content if hasattr(raw_output, "content") else str(raw_output)
    text = text.strip()

    # Look for JSON code blocks or curly braces
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            json_str = text[start:end + 1]
        else:
            json_str = text

    data = json.loads(json_str)
    if "level" in data and isinstance(data["level"], str):
        data["level"] = data["level"].upper().strip()
    return ComplexityDecision.model_validate(data)


class ComplexityAnalyzer:
    """
    LLM-based task complexity analyzer for autonomous document generation.
    Evaluates query intent, document format, planned structure, and context
    to dynamically classify tasks into SMALL, MEDIUM, or LARGE tiers.
    """

    @classmethod
    def _extract_plan_sections_count(cls, doc_plan: Optional[Any]) -> Optional[int]:
        if isinstance(doc_plan, dict) and "sections" in doc_plan:
            raw_sec = doc_plan["sections"]
            if isinstance(raw_sec, list) and len(raw_sec) > 0:
                return len(raw_sec)
        return None

    @classmethod
    def _safe_fallback(
        cls,
        doc_plan: Optional[Any],
        plan_sections_count: Optional[int],
        error_msg: str = ""
    ) -> Dict[str, Any]:
        """
        Minimal safe fallback without keyword-based heuristics.
        Relies strictly on structural section count from plan if already present;
        otherwise defaults safely to SMALL direct execution.
        """
        if plan_sections_count is not None:
            if plan_sections_count >= 4:
                level = ComplexityLevel.LARGE
                use_async = True
            elif plan_sections_count >= 2:
                level = ComplexityLevel.MEDIUM
                use_async = plan_sections_count >= 3
            else:
                level = ComplexityLevel.SMALL
                use_async = False
            sections = plan_sections_count
        else:
            level = ComplexityLevel.SMALL
            sections = 1
            use_async = False

        rationale = f"Safe structural fallback (sections: {sections}) due to decision engine unavailability ({error_msg or 'ok'})."
        logger.info(f"Safe complexity fallback engaged: {level.value} - {rationale}")
        return {
            "level": level,
            "estimated_sections": sections,
            "use_async_subagents": use_async,
            "rationale": rationale,
        }

    @classmethod
    def _build_result(
        cls,
        decision: ComplexityDecision,
        plan_sections_count: Optional[int]
    ) -> Dict[str, Any]:
        estimated_sections = (
            plan_sections_count
            if plan_sections_count is not None
            else max(1, decision.estimated_sections)
        )
        logger.info(f"Complexity analyzed: {decision.level.value} - {decision.rationale}")
        return {
            "level": decision.level,
            "estimated_sections": estimated_sections,
            "use_async_subagents": decision.use_async_subagents,
            "rationale": decision.rationale,
        }

    @classmethod
    def analyze(
        cls,
        query: str,
        doc_format: str,
        doc_plan: Optional[Dict[str, Any]] = None,
        document_context: str = "",
        llm: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Synchronous LLM complexity analysis.
        Uses project's configured model or supplied LLM override.
        """
        plan_sections_count = cls._extract_plan_sections_count(doc_plan)
        user_prompt = _format_user_prompt(query, doc_format, doc_plan, document_context)
        messages = [
            SystemMessage(content=COMPLEXITY_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        try:
            active_llm = llm or get_llm(temperature=0.0)
            decision: Optional[ComplexityDecision] = None

            # 1. Attempt structured output with Pydantic if supported
            if hasattr(active_llm, "with_structured_output"):
                try:
                    structured_model = active_llm.with_structured_output(ComplexityDecision)
                    raw_res = structured_model.invoke(messages)
                    decision = _parse_llm_decision(raw_res)
                except Exception as struct_err:
                    logger.debug(f"with_structured_output failed, falling back to direct prompt: {struct_err}")
                    decision = None

            # 2. Standard JSON prompt invocation fallback
            if decision is None:
                raw_response = active_llm.invoke(messages)
                decision = _parse_llm_decision(raw_response)

            return cls._build_result(decision, plan_sections_count)

        except Exception as e:
            logger.warning(f"Complexity decision LLM call failed: {e}. Using safe minimal fallback.")
            return cls._safe_fallback(doc_plan, plan_sections_count, str(e))

    @classmethod
    async def aanalyze(
        cls,
        query: str,
        doc_format: str,
        doc_plan: Optional[Dict[str, Any]] = None,
        document_context: str = "",
        llm: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Asynchronous LLM complexity analysis.
        Uses project's configured model or supplied LLM override.
        """
        plan_sections_count = cls._extract_plan_sections_count(doc_plan)
        user_prompt = _format_user_prompt(query, doc_format, doc_plan, document_context)
        messages = [
            SystemMessage(content=COMPLEXITY_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        try:
            active_llm = llm or get_llm(temperature=0.0)
            decision: Optional[ComplexityDecision] = None

            # 1. Attempt structured output with Pydantic if supported
            if hasattr(active_llm, "with_structured_output"):
                try:
                    structured_model = active_llm.with_structured_output(ComplexityDecision)
                    raw_res = await structured_model.ainvoke(messages)
                    decision = _parse_llm_decision(raw_res)
                except Exception as struct_err:
                    logger.debug(f"with_structured_output failed, falling back to direct prompt: {struct_err}")
                    decision = None

            # 2. Standard JSON prompt invocation fallback
            if decision is None:
                raw_response = await active_llm.ainvoke(messages)
                decision = _parse_llm_decision(raw_response)

            return cls._build_result(decision, plan_sections_count)

        except Exception as e:
            logger.warning(f"Async complexity decision LLM call failed: {e}. Using safe minimal fallback.")
            return cls._safe_fallback(doc_plan, plan_sections_count, str(e))
