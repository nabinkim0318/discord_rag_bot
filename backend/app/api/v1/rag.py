from datetime import datetime, timezone

from app.core.config import settings
from app.models.rag import RAGQueryRequest, RAGQueryResponse
from fastapi import APIRouter, HTTPException

# ==================== FastAPI Router ====================

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


@router.post("/", response_model=RAGQueryResponse)
async def query_rag(request: RAGQueryRequest):
    """
    RAG-based question response API
    """
    try:
        dummy_response = {
            "answer": f"This answer is generated using {settings.OPENAI_MODEL}.",
            "contexts": [
                {
                    "document_id": "doc-001",
                    "chunk_id": 1,
                    "score": 0.82,
                    "content": "Sample content from document 1.",
                },
                {
                    "document_id": "doc-002",
                    "chunk_id": 3,
                    "score": 0.75,
                    "content": "Sample content from document 2.",
                },
            ],
            "metadata": {
                "pipeline_runtime_ms": 1234,
                "retriever": "FAISS",
                "generator": settings.OPENAI_MODEL,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        return dummy_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
