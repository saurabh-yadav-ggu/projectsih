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

    # Docker Sandbox Configuration
    SANDBOX_ENABLED: bool = os.getenv("SANDBOX_ENABLED", "true").lower() in ("true", "1", "yes")
    SANDBOX_BACKEND: str = os.getenv("SANDBOX_BACKEND", "docker").lower()  # "docker" or "local"
    SANDBOX_IMAGE: str = os.getenv("SANDBOX_IMAGE", "shield-ai-sandbox")
    SANDBOX_NETWORK_DISABLED: bool = os.getenv("SANDBOX_NETWORK_DISABLED", "false").lower() in ("true", "1", "yes")
    SANDBOX_CPU_LIMIT: float = float(os.getenv("SANDBOX_CPU_LIMIT", "2.0"))
    SANDBOX_MEMORY_LIMIT: str = os.getenv("SANDBOX_MEMORY_LIMIT", "2g")
    SANDBOX_TIMEOUT: int = int(os.getenv("SANDBOX_TIMEOUT", "120"))
    SANDBOX_PIDS_LIMIT: int = int(os.getenv("SANDBOX_PIDS_LIMIT", "128"))
    SANDBOX_WORKSPACE_ROOT: str = os.getenv("SANDBOX_WORKSPACE_ROOT", "./workspace")

    # OCR & Scanned Document Configuration
    OCR_ENABLED: bool = os.getenv("OCR_ENABLED", "true").lower() in ("true", "1", "yes")
    OCR_ENGINE: str = os.getenv("OCR_ENGINE", "rapidocr").lower()  # "rapidocr", "paddleocr", "tesseract"
    OCR_DPI: int = int(os.getenv("OCR_DPI", "300"))
    OCR_MIN_TEXT_LENGTH: int = int(os.getenv("OCR_MIN_TEXT_LENGTH", "30"))
    OCR_PREPROCESS: bool = os.getenv("OCR_PREPROCESS", "true").lower() in ("true", "1", "yes")
    OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "eng")
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
