# app/models/feedback.py
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class FeedbackRequest(BaseModel):
    query_id: str = Field(..., description="ID of the query being feedback on")
    feedback_type: Literal["like", "dislike", "report", "improvement"] = Field(
        ..., description="feedback type"
    )
    comment: Optional[str] = Field(None, description="additional comment (optional)")


class FeedbackResponse(BaseModel):
    status: str = Field(..., description="feedback processing status ('success' etc.)")
    message: Optional[str] = Field(None, description="additional message")


class Feedback(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    query_id: str
    feedback: str
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
