from typing import Annotated, List, Optional

from app.core.config import settings
from pydantic import BaseModel, Field

# ==================== Pydantic Models ====================


class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="question text")
    top_k: Optional[Annotated[int, Field(ge=1)]] = Field(
        settings.DEFAULT_TOP_K,
        description="number of documents to retrieve (default 5)",
    )
    use_streaming: Optional[bool] = Field(False, description="streaming response")


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
    contexts: List[RetrievedContext]
    metadata: PipelineMetadata
