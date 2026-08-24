# app/models/rag.py
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings

# ==================== Pydantic Models ====================


class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="question text")
    top_k: int = Field(
        default=settings.DEFAULT_TOP_K,
        ge=1,
        le=settings.MAX_TOP_K,
        description="number of documents to retrieve",
    )
    user_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description=(
            "optional caller metadata for query persistence; not authentication"
        ),
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if value is None or not str(value).strip():
            raise ValueError("query must not be empty or whitespace-only")
        if len(value) > settings.MAX_QUERY_LENGTH:
            raise ValueError(
                f"query must be at most {settings.MAX_QUERY_LENGTH} characters"
            )
        return value


class RetrievedContext(BaseModel):
    document_id: str
    chunk_id: int
    score: float
    content: str


class PipelineMetadata(BaseModel):
    pipeline_runtime_ms: int
    retriever: str
    generator: str
    timestamp: str


class RAGQueryResponse(BaseModel):
    answer: str
    contexts: List[str]  # Simplified: list of strings
    metadata: dict  # Simplified: dictionary
    query_id: Optional[str] = Field(None, description="database query ID for tracking")
