import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document

from app.rag.embeddings import text_splitter, vector_store
from app.rag.pdf_processor import PDFProcessor, PDFProcessingResult

logger = logging.getLogger("app.rag.ingestion")


def process_pdf(
    file_path: str,
    document_id: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> PDFProcessingResult:
    """
    Process a PDF file with per-page OCR and document-type detection.
    Returns PDFProcessingResult with document pages and detailed statistics.
    """
    processor = PDFProcessor()
    return processor.process_pdf(
        file_path=file_path,
        document_id=document_id,
        extra_metadata=extra_metadata,
    )


def load_pdf(file_path: str) -> List[Document]:
    """
    Load a PDF file returning a list of per-page Document objects.
    Each page contains normalized text and rich metadata (page_number, ocr, extraction_method).
    """
    res = process_pdf(file_path)
    return res.documents


def load_text_file(file_path: str) -> List[Document]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    return [
        Document(
            page_content=text,
            metadata={
                "source": str(path),
                "filename": path.name,
                "file_type": "text",
                "page_number": 1,
                "page": 0,
                "ocr": False,
                "extraction_method": "text",
            }
        )
    ]


def load_docx(file_path: str) -> List[Document]:
    import docx
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX not found: {file_path}")
    doc = docx.Document(str(path))
    text_parts = [p.text for p in doc.paragraphs if p.text]
    for table in doc.tables:
        for row in table.rows:
            text_parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    full_text = "\n".join(text_parts)
    return [
        Document(
            page_content=full_text,
            metadata={
                "source": str(path),
                "filename": path.name,
                "file_type": "docx",
                "page_number": 1,
                "page": 0,
                "ocr": False,
                "extraction_method": "text",
            }
        )
    ]


def load_csv(file_path: str) -> List[Document]:
    import csv
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {file_path}")
    lines = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                lines.append(", ".join(row))
    return [
        Document(
            page_content="\n".join(lines),
            metadata={
                "source": str(path),
                "filename": path.name,
                "file_type": "csv",
                "page_number": 1,
                "page": 0,
                "ocr": False,
                "extraction_method": "text",
            }
        )
    ]


def delete_document(
    filename: str,
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> int:
    """
    Remove all chunks associated with a filename (and optionally thread_id / user_id)
    from Chroma vector store to support re-indexing and deletion.
    """
    try:
        filters = []
        if filename:
            filters.append({"filename": {"$eq": filename}})
        if thread_id:
            filters.append({"thread_id": {"$eq": str(thread_id)}})
        if user_id is not None:
            filters.append({"user_id": {"$eq": user_id}})

        if not filters:
            return 0

        where_filter = {"$and": filters} if len(filters) > 1 else filters[0]

        # Query existing IDs to delete
        existing = vector_store._collection.get(where=where_filter)
        ids_to_delete = existing.get("ids", [])
        if ids_to_delete:
            vector_store._collection.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} existing chunks for '{filename}' in thread {thread_id}")
            return len(ids_to_delete)
        return 0
    except Exception as e:
        logger.warning(f"Failed to delete existing chunks for '{filename}': {e}")
        return 0


def add_documents(
    documents: List[Document],
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None,
    deduplicate: bool = True
) -> int:
    """
    Chunk and index documents into Chroma vector store.
    Preserves page-level metadata (page_number, extraction_method, ocr, chunk_id).
    Avoids duplicate chunks when re-indexing existing documents.
    """
    if not documents:
        return 0

    # Deduplicate existing chunks for the same file in this thread if applicable
    if deduplicate and thread_id:
        seen_filenames = {doc.metadata.get("filename") for doc in documents if doc.metadata.get("filename")}
        for fname in seen_filenames:
            delete_document(filename=fname, thread_id=thread_id, user_id=user_id)

    all_chunks: List[Document] = []
    all_chunk_ids: List[str] = []

    for doc in documents:
        # Split each page document independently to guarantee page metadata is never mixed across pages
        chunks = text_splitter.split_documents([doc])
        doc_id = doc.metadata.get("document_id") or "doc"
        page_num = doc.metadata.get("page_number", 1)

        for chunk_idx, chunk in enumerate(chunks, 1):
            chunk_id = f"{doc_id}-p{page_num}-c{chunk_idx:02d}"
            chunk.metadata["chunk_id"] = chunk_id

            if thread_id:
                chunk.metadata["thread_id"] = str(thread_id)
            if user_id is not None:
                chunk.metadata["user_id"] = user_id

            # Ensure page_number is explicitly saved
            chunk.metadata["page_number"] = page_num
            if "page" not in chunk.metadata:
                chunk.metadata["page"] = page_num - 1

            all_chunks.append(chunk)
            all_chunk_ids.append(chunk_id)

    if not all_chunks:
        return 0

    vector_store.add_documents(documents=all_chunks, ids=all_chunk_ids)
    return len(all_chunks)


def add_pdf(
    file_path: str,
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None,
    document_id: Optional[str] = None
) -> int:
    """
    Process PDF with local OCR fallback for scanned pages and index into vector store.
    """
    result = process_pdf(file_path=file_path, document_id=document_id)
    return add_documents(result.documents, thread_id=thread_id, user_id=user_id)


def add_text_file(file_path: str, thread_id: Optional[str] = None, user_id: Optional[int] = None) -> int:
    documents = load_text_file(file_path)
    return add_documents(documents, thread_id=thread_id, user_id=user_id)


def add_docx(file_path: str, thread_id: Optional[str] = None, user_id: Optional[int] = None) -> int:
    documents = load_docx(file_path)
    return add_documents(documents, thread_id=thread_id, user_id=user_id)


def add_csv(file_path: str, thread_id: Optional[str] = None, user_id: Optional[int] = None) -> int:
    documents = load_csv(file_path)
    return add_documents(documents, thread_id=thread_id, user_id=user_id)


def add_file(file_path: str, thread_id: Optional[str] = None, user_id: Optional[int] = None) -> int:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return add_pdf(file_path, thread_id=thread_id, user_id=user_id)
    elif ext in [".txt", ".md"]:
        return add_text_file(file_path, thread_id=thread_id, user_id=user_id)
    elif ext == ".docx":
        return add_docx(file_path, thread_id=thread_id, user_id=user_id)
    elif ext == ".csv":
        return add_csv(file_path, thread_id=thread_id, user_id=user_id)
    return 0
