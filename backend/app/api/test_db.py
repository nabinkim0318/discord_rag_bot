# app/api/test_db.py
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models.query import Query

router = APIRouter()


@router.post("/test-query")
def create_test_query(session: Session = Depends(get_session)):
    test_query = Query(
        user_id="user123",
        query="What is FastAPI?",
        answer="FastAPI is a modern, fast web framework for building APIs.",
        context={"doc1": "FastAPI is Python-based..."},
    )
    session.add(test_query)
    session.commit()
    session.refresh(test_query)
    return test_query
