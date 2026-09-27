import logging
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage

from app.config import settings
from app.core.llm import get_llm
from app.rag import retrieve_context, retrieve_citations, format_citations

logger = logging.getLogger("app.agent.subagents.rag")


async def run_rag_agent(
    query: str,
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None,
    document_context: str = "",
) -> Dict[str, Any]:
    """
    RAG Agent retrieving grounded information from uploaded documents
    with strict thread and user scoping and precise page citations.
    """
    try:
        # Retrieve context if not pre-supplied
        context = document_context
        citations = []
        if not context:
            context = retrieve_context(query=query, k=5, thread_id=thread_id, user_id=user_id)
            citations = retrieve_citations(query=query, k=5, thread_id=thread_id, user_id=user_id)

        if not context:
            return {
                "agent": "rag_agent",
                "success": True,
                "response": "No matching information was found in your uploaded documents for this query.",
                "context_used": "",
                "citations": [],
                "error": None,
            }

        citation_guide = (
            "Always include source citations at the bottom of your answer referencing the document and page numbers:\n"
            "If single source:\n"
            "Source: <filename>\n"
            "Page: <page_number>\n\n"
            "If multiple sources:\n"
            "Sources:\n"
            "- <filename> — Page <page_number>\n\n"
            "Do not fabricate page numbers; only cite from the Document Chunk headers provided."
        )

        prompt = (
            f"You are the Shield AI Knowledge Retrieval Agent.\n"
            f"Answer the user query strictly using the uploaded document context below.\n"
            f"If the answer is not contained in the context, explicitly state that.\n\n"
            f"{citation_guide}\n\n"
            f"--- DOCUMENT CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
            f"User Query: {query}"
        )

        llm = get_llm(temperature=0.1)

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return {
            "agent": "rag_agent",
            "success": True,
            "response": str(response.content),
            "context_used": context,
            "citations": citations,
            "error": None,
        }
    except Exception as e:
        logger.error(f"RAG agent error: {e}")
        return {
            "agent": "rag_agent",
            "success": False,
            "response": f"Failed to retrieve document knowledge: {str(e)}",
            "citations": [],
            "error": str(e),
        }
