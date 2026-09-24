"""
Backward-compatibility facade for the modular RAG package.
Preserves existing import paths while delegating to app.rag.* modules.
"""
from app.rag.embeddings import (
    CHROMA_PERSIST_DIRECTORY,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    OLLAMA_BASE_URL,
    embeddings,
    vector_store,
    text_splitter,
)
from app.rag.ingestion import (
    load_pdf,
    load_text_file,
    add_documents,
    add_pdf,
    add_text_file,
    add_file,
)
from app.rag.retrieval import (
    retrieve_documents,
    retrieve_context,
)

__all__ = [
    "CHROMA_PERSIST_DIRECTORY",
    "COLLECTION_NAME",
    "EMBEDDING_MODEL",
    "OLLAMA_BASE_URL",
    "embeddings",
    "vector_store",
    "text_splitter",
    "load_pdf",
    "load_text_file",
    "add_documents",
    "add_pdf",
    "add_text_file",
    "add_file",
    "retrieve_documents",
    "retrieve_context",
]