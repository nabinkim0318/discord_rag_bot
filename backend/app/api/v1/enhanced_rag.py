# backend/app/api/v1/enhanced_rag.py
"""
Enhanced RAG API endpoints
- Query decomposition and intent detection
- Multi-route search
- Discord-optimized responses
"""

from fastapi import APIRouter, Request

from app.core.metrics import record_failure_metric
from app.models.rag import RAGQueryRequest, RAGQueryResponse
from app.services.enhanced_rag_service import run_enhanced_rag_pipeline

# ==================== FastAPI Router ====================

enhanced_rag_router = APIRouter(prefix="/api/v1/enhanced-rag", tags=["Enhanced RAG"])


@enhanced_rag_router.post("/", response_model=RAGQueryResponse)
async def enhanced_query_rag(request: RAGQueryRequest, http_request: Request):
    """
    Enhanced RAG query processing

    - Query decomposition and intent detection
    - Multi-route search
    - Discord-optimized response generation
    """
    try:
        # Extract user information from headers
        user_id = http_request.headers.get("X-User-ID")
        channel_id = http_request.headers.get("X-Channel-ID")
        request_id = http_request.headers.get("X-Request-ID")

        # Run enhanced RAG pipeline
        answer, contexts, metadata = run_enhanced_rag_pipeline(
            query=request.query,
            top_k=request.top_k or 5,
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
        record_failure_metric("/api/v1/enhanced-rag/", "pipeline_error")
        from app.core.exceptions import RAGException

        raise RAGException(
            message=f"Enhanced RAG pipeline failed: {str(e)}",
            error_code="ENHANCED_RAG_PIPELINE_ERROR",
            details={
                "stage": "enhanced_generation",
                "endpoint": "/api/v1/enhanced-rag/",
            },
        )


@enhanced_rag_router.get("/health")
async def enhanced_rag_health():
    """Enhanced RAG service health check"""
    try:
        # Check service status with simple test query
        test_query = "test query"
        answer, contexts, metadata = run_enhanced_rag_pipeline(
            query=test_query, top_k=1
        )

        return {
            "status": "healthy",
            "service": "enhanced-rag",
            "test_query_processed": True,
            "metadata": {
                "total_time": metadata.get("total_time", 0),
                "retrieval_time": metadata.get("retrieval_time", 0),
                "generation_time": metadata.get("generation_time", 0),
            },
        }

    except Exception as e:
        return {"status": "unhealthy", "service": "enhanced-rag", "error": str(e)}
