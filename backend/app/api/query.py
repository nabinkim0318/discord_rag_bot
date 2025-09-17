# app/api/query.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.logging import logger
from app.db.session import get_session
from app.models.query import Query
from app.models.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import run_rag_pipeline

router = APIRouter()


@router.post("/", response_model=RAGQueryResponse)
async def query_rag(request: RAGQueryRequest, session: Session = Depends(get_session)):
    """
    RAG query processing and database storage
    """
    try:
        logger.info(f"Processing RAG query: {request.query}")

        # Run RAG pipeline
        answer, contexts, metadata = run_rag_pipeline(request.query, request.top_k or 5)

        # Save query result to database
        query_record = Query(
            user_id=request.user_id if hasattr(request, "user_id") else None,
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

        logger.info(f"Query saved to database with ID: {query_record.id}")

        # Store RAG result in Weaviate with query_id
        from app.services.rag_service import _store_rag_result_in_weaviate

        _store_rag_result_in_weaviate(
            query=request.query,
            answer=answer,
            contexts=contexts,
            metadata=metadata,
            query_id=query_record.id,
        )

        return {
            "answer": answer,
            "contexts": contexts,
            "metadata": metadata,
            "query_id": query_record.id,  # Added: return saved query ID
        }

    except Exception as e:
        logger.error(f"RAG query failed: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Query processing failed: {str(e)}"
        )


@router.get("/queries/", response_model=List[Query])
def get_queries(session: Session = Depends(get_session)):
    return session.exec(select(Query)).all()
