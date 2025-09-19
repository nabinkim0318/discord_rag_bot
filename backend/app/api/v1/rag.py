# app/api/v1/rag.py

from fastapi import APIRouter, HTTPException, Request

from app.core.metrics import record_failure_metric
from app.models.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import run_rag_pipeline

# ==================== FastAPI Router ====================

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


@router.post("/", response_model=RAGQueryResponse)
async def query_rag(request: RAGQueryRequest, http_request: Request):
    try:
        user_id = http_request.headers.get("X-User-ID")
        channel_id = http_request.headers.get("X-Channel-ID")
        request_id = http_request.headers.get("X-Request-ID")

        answer, contexts, metadata = run_rag_pipeline(
            request.query,
            request.top_k or 5,
            user_id=user_id,
            channel_id=channel_id,
            request_id=request_id,
        )
        return {
            "answer": answer,
            "contexts": contexts,
            "metadata": metadata,
        }
    except Exception as e:
        record_failure_metric("/api/v1/rag/", "pipeline_error")
        raise HTTPException(status_code=500, detail=str(e))
