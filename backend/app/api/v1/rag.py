# app/api/v1/rag.py

from fastapi import APIRouter, HTTPException

from app.core.metrics import record_failure_metric
from app.models.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import run_rag_pipeline

# ==================== FastAPI Router ====================

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


@router.post("/", response_model=RAGQueryResponse)
async def query_rag(request: RAGQueryRequest):
    try:
        answer, contexts, metadata = run_rag_pipeline(request.query)
        return {
            "answer": answer,
            "contexts": contexts,
            "metadata": metadata,
        }
    except Exception as e:
        record_failure_metric("/api/v1/rag/", "pipeline_error")
        raise HTTPException(status_code=500, detail=str(e))
