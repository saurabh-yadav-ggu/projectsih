from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter


# =========================================================
# Configuration
# =========================================================

CHROMA_PERSIST_DIRECTORY = "./chroma_db"

COLLECTION_NAME = "documents"

EMBEDDING_MODEL = "qwen3-embedding:0.6b"

OLLAMA_BASE_URL = "http://localhost:11434"


# =========================================================
# Embedding Model
# =========================================================

embeddings = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=OLLAMA_BASE_URL,
)


# =========================================================
# ChromaDB
# =========================================================

vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=CHROMA_PERSIST_DIRECTORY,
)


# =========================================================
# Text Splitter
# =========================================================

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)


# =========================================================
# Load PDF
# =========================================================

def load_pdf(
    file_path: str,
) -> List[Document]:
    """
    Load a PDF using pypdf through PyPDFLoader.

    Each PDF page becomes a LangChain Document.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"PDF not found: {file_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {file_path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            "File must be a PDF."
        )

    loader = PyPDFLoader(
        str(path)
    )

    documents = loader.load()

    return documents


# =========================================================
# Load Text File
# =========================================================

def load_text_file(
    file_path: str,
) -> List[Document]:
    """
    Load a normal text file.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    text = path.read_text(
        encoding="utf-8"
    )

    return [
        Document(
            page_content=text,
            metadata={
                "source": str(path)
            },
        )
    ]


# =========================================================
# Split Documents
# =========================================================

def split_documents(
    documents: List[Document],
) -> List[Document]:
    """
    Split documents into smaller chunks.
    """

    return text_splitter.split_documents(
        documents
    )


# =========================================================
# Add Documents to Chroma
# =========================================================

def add_documents(
    documents: List[Document],
) -> int:
    """
    Split documents and store their embeddings
    in ChromaDB.
    """

    chunks = split_documents(
        documents
    )

    if not chunks:
        return 0

    vector_store.add_documents(
        documents=chunks
    )

    return len(chunks)


# =========================================================
# Add PDF
# =========================================================

def add_pdf(
    file_path: str,
) -> int:
    """
    Load a PDF, split it into chunks,
    generate embeddings and store them in ChromaDB.
    """

    documents = load_pdf(
        file_path
    )

    # Add useful metadata
    for document in documents:
        document.metadata["file_type"] = "pdf"

    return add_documents(
        documents
    )


# =========================================================
# Add Text File
# =========================================================

def add_text_file(
    file_path: str,
) -> int:
    """
    Load and index a text file.
    """

    documents = load_text_file(
        file_path
    )

    for document in documents:
        document.metadata["file_type"] = "text"

    return add_documents(
        documents
    )


# =========================================================
# Add File Automatically
# =========================================================

def add_file(
    file_path: str,
) -> int:
    """
    Automatically detect the file type.
    """

    extension = Path(
        file_path
    ).suffix.lower()

    if extension == ".pdf":
        return add_pdf(
            file_path
        )

    elif extension in [
        ".txt",
        ".md",
    ]:
        return add_text_file(
            file_path
        )

    else:
        raise ValueError(
            f"Unsupported file type: {extension}"
        )


# =========================================================
# Similarity Search
# =========================================================

def search_documents(
    query: str,
    k: int = 4,
) -> List[Document]:
    """
    Search ChromaDB for relevant documents.
    """

    results = vector_store.similarity_search(
        query=query,
        k=k,
    )

    return results


# =========================================================
# Retrieve RAG Context
# =========================================================

def retrieve_context(
    query: str,
    k: int = 4,
) -> str:
    """
    Retrieve relevant chunks and convert them
    into context for the LLM.
    """

    documents = search_documents(
        query=query,
        k=k,
    )

    if not documents:
        return "No relevant information found."

    context_parts = []

    for index, document in enumerate(
        documents,
        start=1,
    ):

        source = document.metadata.get(
            "source",
            "unknown",
        )

        page = document.metadata.get(
            "page",
            None,
        )

        if page is not None:
            page_info = f"Page: {page + 1}"
        else:
            page_info = ""

        context_parts.append(
            f"""
Document {index}
Source: {source}
{page_info}

{document.page_content}
"""
        )

    return "\n".join(
        context_parts
    )


# =========================================================
# Get Number of Stored Chunks
# =========================================================

def get_document_count() -> int:
    """
    Return the number of chunks stored in ChromaDB.
    """

    return vector_store._collection.count()


# =========================================================
# Clear ChromaDB
# =========================================================

def clear_vector_store():
    """
    Delete the ChromaDB collection.
    """

    vector_store.delete_collection()