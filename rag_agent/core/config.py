# rag_agent/core/config.py
"""
Configuration settings for rag_agent to use backend settings
"""
from typing import Optional

from pydantic import BaseSettings

from ._bootstrap import attach_backend_path, get_fallback_logger

# Attach backend path
attach_backend_path()
logger = get_fallback_logger()


class _AgentSettings(BaseSettings):
    """Rag_agent local settings with pydantic validation"""

    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_API_BASE_URL: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    JINA_API_KEY: Optional[str] = None
    PROMPT_TOKEN_BUDGET: int = 4000
    GENERATION_MAX_TOKENS: int = 1000
    WEAVIATE_URL: str = "http://localhost:8080"
    WEAVIATE_API_KEY: Optional[str] = None
    WEAVIATE_CLASS_NAME: str = "RAGDocument"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Try to import backend settings first
try:
    from app.core.config import settings as _backend_settings

    settings = _backend_settings
    logger.info("Using backend settings for rag_agent")
except Exception as e:
    logger.warning("Using rag_agent local settings fallback: %s", e)
    settings = _AgentSettings()  # env 기반 로드

# export settings
__all__ = ["settings"]
