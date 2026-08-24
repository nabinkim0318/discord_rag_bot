# app/api/query.py
from time import perf_counter

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.core.exceptions import ExternalServiceException, RAGException
from app.core.logging import logger
from app.core.metrics import (
    rag_query_counter,
    rag_query_latency,
    record_failure_metric,
)
from app.core.request_id import get_request_id
from app.db.session import get_session
from app.models.query import Query
from app.models.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import run_rag_pipeline

query_router = APIRouter()


@query_router.post("/", response_model=RAGQueryResponse)
def query_rag(
    request: RAGQueryRequest,
    http_request: Request,
    session: Session = Depends(get_session),
):
    """
    RAG query processing and database storage
    """
    start = perf_counter()
    try:
        request_id = get_request_id(http_request)
        # Body user_id is optional persistence metadata, not authentication.
        user_id = request.user_id

        answer, contexts, metadata = run_rag_pipeline(
            request.query,
            request.top_k,
            request_id=request_id,
        )

        query_record = Query(
            user_id=user_id,
            query=request.query,
            answer=answer,
            context={
                "contexts": contexts,
                "metadata": metadata,
                "top_k": request.top_k,
            },
        )

        session.add(query_record)
        session.commit()
        session.refresh(query_record)

        logger.bind(request_id=request_id, query_id=query_record.id).info(
            "Query saved to database"
        )

        dur = perf_counter() - start
        rag_query_counter.labels(method="POST", endpoint="/api/query/").inc()
        rag_query_latency.labels(endpoint="/api/query/").observe(dur)

        return {
            "answer": answer,
            "contexts": contexts,
            "metadata": metadata,
            "query_id": query_record.id,
        }

    except Exception as exc:
        logger.exception("RAG query failed")
        try:
            session.rollback()
        except Exception:
            pass  # Session might already be closed

        error_code = getattr(exc, "error_code", "QUERY_PROCESSING_ERROR")
        record_failure_metric("/api/query/", error_code)

        if isinstance(exc, RAGException):
            raise
        if isinstance(exc, ExternalServiceException):
            raise ExternalServiceException(
                message="RAG dependency is temporarily unavailable",
                error_code=exc.error_code,
                service_name=exc.service_name,
                details={"endpoint": "/api/query/"},
            ) from exc
        raise RAGException(
            message="RAG service is temporarily unavailable",
            error_code="QUERY_PROCESSING_ERROR",
            details={"stage": "query_processing", "endpoint": "/api/query/"},
        ) from exc
