from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

# =========================================================
# Configuration
# =========================================================

CHROMA_PERSIST_DIRECTORY = settings.CHROMA_PERSIST_DIRECTORY
COLLECTION_NAME = "documents"
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL


# =========================================================
# Embedding Model & ChromaDB
# =========================================================

embeddings = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=OLLAMA_BASE_URL,
)

vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=CHROMA_PERSIST_DIRECTORY,
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)


# =========================================================
# Loaders
# =========================================================

def load_pdf(file_path: str) -> List[Document]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("File must be a PDF.")

    loader = PyPDFLoader(str(path))
    return loader.load()


def load_text_file(file_path: str) -> List[Document]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    return [
        Document(
            page_content=text,
            metadata={"source": str(path)}
        )
    ]


# =========================================================
# Document Storage with Thread ID Scoping
# =========================================================

def add_documents(
    documents: List[Document],
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> int:
    chunks = text_splitter.split_documents(documents)
    if not chunks:
        return 0

    for chunk in chunks:
        if thread_id:
            chunk.metadata["thread_id"] = str(thread_id)
        if user_id:
            chunk.metadata["user_id"] = user_id

    vector_store.add_documents(documents=chunks)
    return len(chunks)


def add_pdf(file_path: str, thread_id: Optional[str] = None, user_id: Optional[int] = None) -> int:
    documents = load_pdf(file_path)
    filename = Path(file_path).name
    for doc in documents:
        doc.metadata["file_type"] = "pdf"
        doc.metadata["filename"] = filename
    return add_documents(documents, thread_id=thread_id, user_id=user_id)


def add_text_file(file_path: str, thread_id: Optional[str] = None, user_id: Optional[int] = None) -> int:
    documents = load_text_file(file_path)
    filename = Path(file_path).name
    for doc in documents:
        doc.metadata["file_type"] = "text"
        doc.metadata["filename"] = filename
    return add_documents(documents, thread_id=thread_id, user_id=user_id)


def add_image_file(file_path: str, thread_id: Optional[str] = None, user_id: Optional[int] = None) -> int:
    from app.vision import analyze_image
    filename = Path(file_path).name
    description = analyze_image(
        file_path,
        question="Describe this image in full detail, including all visible text, numbers, diagrams, and features."
    )
    doc = Document(
        page_content=f"Uploaded Image: {filename}\nVisual Analysis:\n{description}",
        metadata={
            "source": file_path,
            "filename": filename,
            "file_type": "image",
            "image_path": file_path
        }
    )
    return add_documents([doc], thread_id=thread_id, user_id=user_id)


def add_file(file_path: str, thread_id: Optional[str] = None, user_id: Optional[int] = None) -> int:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return add_pdf(file_path, thread_id=thread_id, user_id=user_id)
    elif ext in [".txt", ".md"]:
        return add_text_file(file_path, thread_id=thread_id, user_id=user_id)
    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        return add_image_file(file_path, thread_id=thread_id, user_id=user_id)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# =========================================================
# Retrieval & Thread Context
# =========================================================

def search_documents(query: str, k: int = 6, thread_id: Optional[str] = None) -> List[Document]:
    if thread_id:
        try:
            results = vector_store.similarity_search(
                query=query,
                k=k,
                filter={"thread_id": str(thread_id)}
            )
            if results:
                return results
        except Exception:
            pass

    # Fallback to general similarity search
    return vector_store.similarity_search(query=query, k=k)


def get_thread_documents_context(thread_id: str, max_chunks: int = 8) -> str:
    """Retrieve all document chunks for a specific thread_id to construct complete prompt context."""
    if not thread_id:
        return ""
    try:
        results = vector_store.similarity_search(
            query="document overview summary content",
            k=max_chunks,
            filter={"thread_id": str(thread_id)}
        )
        if not results:
            return ""

        context_parts = []
        for idx, doc in enumerate(results, start=1):
            fn = doc.metadata.get("filename", Path(doc.metadata.get("source", "file")).name)
            page = doc.metadata.get("page")
            p_info = f" (Page {page + 1})" if page is not None else ""
            context_parts.append(f"--- Chunk {idx} from {fn}{p_info} ---\n{doc.page_content}")
        return "\n\n".join(context_parts)
    except Exception:
        return ""


def retrieve_context(query: str, k: int = 6, thread_id: Optional[str] = None) -> str:
    # If query is generic ("explain this document", "summarize", etc.), grab thread context directly
    generic_keywords = ["explain", "summarize", "overview", "what is this", "document", "pdf", "file", "contents", "details"]
    is_generic = any(kw in query.lower() for kw in generic_keywords)

    if is_generic and thread_id:
        thread_ctx = get_thread_documents_context(thread_id, max_chunks=k)
        if thread_ctx:
            return thread_ctx

    documents = search_documents(query=query, k=k, thread_id=thread_id)

    if not documents and thread_id:
        thread_ctx = get_thread_documents_context(thread_id, max_chunks=k)
        if thread_ctx:
            return thread_ctx

    if not documents:
        return "No relevant document chunks found in knowledge base."

    context_parts = []
    for index, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page")
        page_info = f"Page: {page + 1}" if page is not None else ""

        context_parts.append(
            f"Document Chunk {index} | Source: {source} | {page_info}\n{doc.page_content}"
        )

    return "\n\n".join(context_parts)


def get_document_count() -> int:
    return vector_store._collection.count()


def clear_vector_store():
    vector_store.delete_collection()