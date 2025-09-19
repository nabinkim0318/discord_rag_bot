# app/models/rag.py
from typing import Annotated, List, Optional

from pydantic import BaseModel, Field

from app.core.config import settings

# ==================== Pydantic Models ====================


class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="question text")
    top_k: Optional[Annotated[int, Field(ge=1)]] = Field(
        settings.DEFAULT_TOP_K,
        description="number of documents to retrieve (default 5)",
    )
    use_streaming: Optional[bool] = Field(False, description="streaming response")
    user_id: Optional[str] = Field(None, description="user identifier for tracking")


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
