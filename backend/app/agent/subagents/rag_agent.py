import logging
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage

from app.config import settings
from app.core.llm import get_llm
from app.rag import retrieve_context

logger = logging.getLogger("app.agent.subagents.rag")


async def run_rag_agent(
    query: str,
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None,
    document_context: str = "",
) -> Dict[str, Any]:
    """
    RAG Agent retrieving grounded information from uploaded documents
    with strict thread and user scoping.
    """
    try:
        # Retrieve context if not pre-supplied
        context = document_context
        if not context:
            context = retrieve_context(query=query, k=5, thread_id=thread_id, user_id=user_id)

        if not context:
            return {
                "agent": "rag_agent",
                "success": True,
                "response": "No matching information was found in your uploaded documents for this query.",
                "context_used": "",
                "error": None,
            }

        prompt = (
            f"You are the Shield AI Knowledge Retrieval Agent.\n"
            f"Answer the user query strictly using the uploaded document context below.\n"
            f"If the answer is not contained in the context, explicitly state that.\n"
            f"Cite the source documents when available.\n\n"
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
            "error": None,
        }
    except Exception as e:
        logger.error(f"RAG agent error: {e}")
        return {
            "agent": "rag_agent",
            "success": False,
            "response": f"Failed to retrieve document knowledge: {str(e)}",
            "error": str(e),
        }
