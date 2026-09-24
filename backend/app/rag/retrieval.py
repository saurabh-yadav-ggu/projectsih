from typing import List, Optional
from langchain_core.documents import Document

from app.rag.embeddings import vector_store


def retrieve_documents(
    query: str,
    k: int = 4,
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> List[Document]:
    conditions = []
    if thread_id:
        conditions.append({"thread_id": {"$eq": str(thread_id)}})
    if user_id is not None:
        conditions.append({"user_id": {"$eq": user_id}})

    if len(conditions) > 1:
        search_filter = {"$and": conditions}
    elif len(conditions) == 1:
        search_filter = conditions[0]
    else:
        search_filter = None

    results: List[Document] = []

    # 1. Similarity search with thread + user scoping
    try:
        if search_filter:
            results = vector_store.similarity_search(query, k=k, filter=search_filter)
        else:
            results = vector_store.similarity_search(query, k=k)
    except Exception:
        results = []

    # 2. Direct document fallback: If query phrasing was broad (e.g. "summarize")
    # retrieve raw chunks ONLY for this specific thread_id if documents exist in this thread
    if not results and thread_id:
        try:
            data = vector_store.get(where={"thread_id": str(thread_id)}, limit=k)
            if data and data.get("documents"):
                fallback_docs = []
                for doc_text, meta in zip(data["documents"], data.get("metadatas", [])):
                    fallback_docs.append(Document(page_content=doc_text, metadata=meta or {}))
                results = fallback_docs
        except Exception:
            pass

    return results


def retrieve_context(
    query: str,
    k: int = 4,
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> str:
    docs = retrieve_documents(query=query, k=k, thread_id=thread_id, user_id=user_id)
    if not docs:
        return ""

    context_parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("filename") or doc.metadata.get("source") or "Unknown"
        page = doc.metadata.get("page")
        page_info = f" (Page {page + 1})" if page is not None else ""
        context_parts.append(
            f"--- Document Chunk {i} from {source}{page_info} ---\n{doc.page_content.strip()}"
        )

    return "\n\n".join(context_parts)
