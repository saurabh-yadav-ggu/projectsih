import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Shield AI"
    VERSION: str = "1.0.0"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "ministral-3:3b")
    VISION_MODEL: str = os.getenv("VISION_MODEL", "ministral-3:3b")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "embeddinggemma")
    CHROMA_PERSIST_DIRECTORY: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "shield-ai-secret-key-production-change-me")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
