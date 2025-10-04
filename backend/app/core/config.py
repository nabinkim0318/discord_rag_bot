# app/core/config.py
"""
Configuration settings for the RAG Backend API
"""

import os
from pathlib import Path
from typing import List, Optional


class Settings:
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
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_API_BASE_URL: Optional[str] = os.getenv("LLM_API_BASE_URL")

    # ==================== Token budgets ====================
    GENERATION_MAX_TOKENS: int = int(os.getenv("GENERATION_MAX_TOKENS", "512"))
    PROMPT_TOKEN_BUDGET: int = int(os.getenv("PROMPT_TOKEN_BUDGET", "6000"))

    # ==================== Cohere/Jina reranker ====================
    COHERE_API_KEY: Optional[str] = os.getenv("COHERE_API_KEY")
    JINA_API_KEY: Optional[str] = os.getenv("JINA_API_KEY")

    # ==================== Azure OpenAI ====================
    AZURE_OPENAI_API_KEY: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    # ==================== Weaviate Settings ====================
    WEAVIATE_URL: str = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
    WEAVIATE_API_KEY: Optional[str] = os.getenv("WEAVIATE_API_KEY")
    WEAVIATE_CLASS_NAME: str = os.getenv("WEAVIATE_CLASS_NAME", "KBChunk")
    WEAVIATE_BATCH_SIZE: int = int(os.getenv("WEAVIATE_BATCH_SIZE", "100"))

    # ==================== Database Settings ====================
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # ==================== Security Settings ====================
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # ==================== CORS Settings ====================
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001,"
        "http://localhost:8001,http://localhost:9090",
    ).split(",")
    CORS_ALLOW_CREDENTIALS: bool = (
        os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    )

    # ==================== Rate Limiting ====================
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # ==================== Metrics Settings ====================
    METRICS_ENABLED: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    METRICS_PATH: str = os.getenv("METRICS_PATH", "/metrics")


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
