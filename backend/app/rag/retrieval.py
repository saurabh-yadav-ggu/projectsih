from typing import List, Optional, Dict, Any
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


def retrieve_citations(
    query: str,
    k: int = 4,
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None,
    docs: Optional[List[Document]] = None,
) -> List[Dict[str, Any]]:
    """
    Extract unique, verifiable citations from retrieved document chunks.
    Guarantees page numbers originate directly from document metadata.
    """
    if docs is None:
        docs = retrieve_documents(query=query, k=k, thread_id=thread_id, user_id=user_id)

    citations: List[Dict[str, Any]] = []
    seen = set()

    for doc in docs:
        source = doc.metadata.get("filename") or doc.metadata.get("source") or "Unknown"
        page = doc.metadata.get("page_number")
        if page is None and doc.metadata.get("page") is not None:
            page = doc.metadata.get("page") + 1

        key = (source, page)
        if key not in seen:
            seen.add(key)
            citations.append({
                "source": source,
                "page": page,
                "ocr": doc.metadata.get("ocr", False),
                "extraction_method": doc.metadata.get("extraction_method", "text"),
                "ocr_confidence": doc.metadata.get("ocr_confidence"),
                "chunk_id": doc.metadata.get("chunk_id"),
            })

    return citations


def format_citations(citations: List[Dict[str, Any]]) -> str:
    """
    Format citation list into a clean, human-readable citation block.
    Example single source:
        Source: plant_inspection.pdf
        Page: 24
    Example multiple sources:
        Sources:
        - plant_inspection.pdf — Page 24
        - inspection_report.pdf — Page 8
    """
    if not citations:
        return ""

    if len(citations) == 1:
        c = citations[0]
        page_str = f"\nPage: {c['page']}" if c.get("page") is not None else ""
        return f"Source: {c['source']}{page_str}"

    lines = ["Sources:"]
    for c in citations:
        page_str = f" — Page {c['page']}" if c.get("page") is not None else ""
        lines.append(f"- {c['source']}{page_str}")
    return "\n".join(lines)


def retrieve_context(
    query: str,
    k: int = 4,
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> str:
    """
    Retrieve document chunks formatted as clean context blocks for LLM consumption.
    Preserves document filename, page number, and extraction method flags.
    """
    docs = retrieve_documents(query=query, k=k, thread_id=thread_id, user_id=user_id)
    if not docs:
        return ""

    context_parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("filename") or doc.metadata.get("source") or "Unknown"
        page = doc.metadata.get("page_number")
        if page is None and doc.metadata.get("page") is not None:
            page = doc.metadata.get("page") + 1

        page_info = f" (Page {page})" if page is not None else ""
        is_ocr = doc.metadata.get("ocr", False)
        ocr_tag = " [OCR]" if is_ocr else ""

        context_parts.append(
            f"--- Document Chunk {i} from {source}{page_info}{ocr_tag} ---\n{doc.page_content.strip()}"
        )

    return "\n\n".join(context_parts)
