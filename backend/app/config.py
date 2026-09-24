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
    VISION_MODEL: str = os.getenv("VISION_MODEL", "moondream")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "embeddinggemma")
    CHROMA_PERSIST_DIRECTORY: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "shield-ai-super-secret-jwt-token-key-production-32bytes")

    # Mistral AI Cloud API Configuration
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "mstrl_ld5Rq88TClNFiBvo0iLOFOK96jYUQFLq_1LsYpv")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "ministral-3b-latest")
    MISTRAL_VISION_MODEL: str = os.getenv("MISTRAL_VISION_MODEL", "pixtral-12b-2409")
    USE_MISTRAL_API: bool = os.getenv("USE_MISTRAL_API", "true").lower() in ("true", "1", "yes")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
