from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

CHROMA_PERSIST_DIRECTORY = settings.CHROMA_PERSIST_DIRECTORY
COLLECTION_NAME = "documents"
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL

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
