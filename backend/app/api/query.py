# app/api/query.py
from time import perf_counter
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.core.logging import logger
from app.core.metrics import rag_query_counter, rag_query_latency
from app.db.session import get_session
from app.models.query import Query
from app.models.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import run_rag_pipeline

query_router = APIRouter()


@query_router.post("/", response_model=RAGQueryResponse)
async def query_rag(
    request: RAGQueryRequest,
    session: Session = Depends(get_session),
    http_request: Request = None,
):
    """
    RAG query processing and database storage
    """
    start = perf_counter()
    try:
        # Extract tracing/user context
        user_id = request.user_id  # Default from request body
        channel_id = None
        request_id = None
        try:
            if http_request is not None:
                # Override with header values if present
                header_user_id = http_request.headers.get("X-User-ID")
                if header_user_id:
                    user_id = header_user_id
                channel_id = http_request.headers.get("X-Channel-ID")
                request_id = http_request.headers.get("X-Request-ID")
        except Exception:
            pass

        logger.info(
            "Processing RAG query: {}",
            request.query,
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "channel_id": channel_id,
            },
        )

        # Run RAG pipeline
        answer, contexts, metadata = run_rag_pipeline(
            request.query,
            request.top_k or 5,
            user_id=user_id,
            channel_id=channel_id,
            request_id=request_id,
        )

        # Save query result to database
        query_record = Query(
            user_id=user_id,  # Use the extracted/override user_id
            query=request.query,
            answer=answer,
            context={
                "contexts": contexts,
                "metadata": metadata,
                "top_k": getattr(request, "top_k", 5),
                "use_streaming": getattr(request, "use_streaming", False),
            },
        )

        session.add(query_record)
        session.commit()
        session.refresh(query_record)

        logger.info(
            "Query saved to database with ID: {}",
            query_record.id,
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "query_id": query_record.id,
            },
        )

        # Store RAG result in Weaviate with actual query_id
        from app.services.rag_service import store_rag_result_in_weaviate

        store_rag_result_in_weaviate(
            query=request.query,
            answer=answer,
            contexts=contexts,
            metadata=metadata,
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

    except Exception as e:
        logger.error(f"RAG query failed: {str(e)}")
        try:
            session.rollback()
        except Exception:
            pass  # Session might already be closed
        from app.core.exceptions import RAGException

        raise RAGException(
            message=f"Query processing failed: {str(e)}",
            error_code="QUERY_PROCESSING_ERROR",
            details={"stage": "query_processing", "endpoint": "/api/query/"},
        )


@query_router.get("/queries/", response_model=List[Query])
def get_queries(session: Session = Depends(get_session)):
    return session.exec(select(Query)).all()
