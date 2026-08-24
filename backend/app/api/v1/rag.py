# app/api/v1/rag.py

from fastapi import APIRouter, Request

from app.core.exceptions import ExternalServiceException, RAGException
from app.core.metrics import record_failure_metric
from app.core.request_id import get_request_id
from app.models.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import run_rag_pipeline

# ==================== FastAPI Router ====================

rag_router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


@rag_router.post("/", response_model=RAGQueryResponse)
def query_rag(request: RAGQueryRequest, http_request: Request):
    try:
        request_id = get_request_id(http_request)

        answer, contexts, metadata = run_rag_pipeline(
            request.query,
            request.top_k,
            request_id=request_id,
        )
        return {
            "answer": answer,
            "contexts": contexts,
            "metadata": metadata,
        }
    except RAGException as exc:
        record_failure_metric("/api/v1/rag/", exc.error_code)
        raise
    except ExternalServiceException as exc:
        record_failure_metric("/api/v1/rag/", exc.error_code)
        raise ExternalServiceException(
            message="RAG dependency is temporarily unavailable",
            error_code=exc.error_code,
            service_name=exc.service_name,
            details={"endpoint": "/api/v1/rag/"},
        ) from exc
    except Exception as exc:
        record_failure_metric("/api/v1/rag/", "RAG_PIPELINE_ERROR")
        raise RAGException(
            message="RAG service is temporarily unavailable",
            error_code="RAG_PIPELINE_ERROR",
            details={
                "stage": "generation",
                "endpoint": "/api/v1/rag/",
                "exception_type": type(exc).__name__,
            },
        ) from exc
