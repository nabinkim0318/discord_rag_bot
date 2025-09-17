# app/models/feedback.py
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel
from sqlmodel import Field, SQLModel, UniqueConstraint


class FeedbackType(str, Enum):
    up = "up"
    down = "down"


class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("query_id", "user_id", name="uq_feedback_query_user"),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, index=True)
    query_id: str = Field(foreign_key="queries.id", index=True)
    user_id: str = Field(index=True)
    feedback: FeedbackType  # enum-backed column
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# request/response schema (already used form)


class FeedbackRequest(BaseModel):
    query_id: str
    feedback_type: FeedbackType  # API input is feedback_type


class FeedbackResponse(BaseModel):
    status: str
    message: str
    feedback_id: str
