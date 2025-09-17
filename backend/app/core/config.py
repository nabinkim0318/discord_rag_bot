# app/core/config.py
"""
Configuration settings for the RAG Backend API
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings"""

    # ==================== Basic App Settings ====================
    APP_NAME: str = "RAG API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ==================== Server Settings ====================
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # ==================== Logging Settings ====================
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = Path("logs")
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "7 days"

    # ==================== RAG Agent Settings ====================
    RAG_AGENT_PATH: Path = Path("../rag_agent")
    DEFAULT_TOP_K: int = 5
    MAX_TOP_K: int = 20

    # ==================== External API Settings ====================
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 1000

    # ==================== Weaviate Settings ====================
    WEAVIATE_URL: str = "http://localhost:8080"
    WEAVIATE_API_KEY: Optional[str] = None
    WEAVIATE_CLASS_NAME: str = "RAGDocument"
    WEAVIATE_BATCH_SIZE: int = 100

    # ==================== Database Settings ====================
    DATABASE_URL: Optional[str] = None

    # ==================== Security Settings ====================
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ==================== CORS Settings ====================
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True

    # ==================== Rate Limiting ====================
    RATE_LIMIT_PER_MINUTE: int = 60

    # ==================== Metrics Settings ====================
    METRICS_ENABLED: bool = True
    METRICS_PATH: str = "/metrics"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


# ==================== Utility Functions ====================
def get_log_dir() -> Path:
    """Get the log directory path"""
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    return settings.LOG_DIR.resolve()


def get_rag_agent_path() -> Path:
    """Get the RAG agent path"""
    rag_path = settings.RAG_AGENT_PATH
    if not rag_path.is_absolute():
        rag_path = (
            Path(__file__).resolve().parent.parent.parent.parent / rag_path
        ).resolve()
    return rag_path
