from typing import Literal, Optional

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    query: str = Field(..., description="question text")
    answer: str = Field(..., description="provided answer")
    feedback_type: Literal["like", "dislike", "report", "improvement"] = Field(
        ..., description="feedback type"
    )
    comment: Optional[str] = Field(None, description="additional comment (optional)")


class FeedbackResponse(BaseModel):
    status: str = Field(..., description="feedback processing status ('success' etc.)")
    message: Optional[str] = Field(None, description="additional message")
