"""
Feedback database models
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class FeedbackBase(SQLModel):
    """Base feedback model"""

    query_id: str = Field(foreign_key="queries.id", description="Reference to query")
    user_id: str = Field(description="Discord user ID")
    score: str = Field(description="Feedback score: 'up' or 'down'")
    comment: Optional[str] = Field(default=None, description="Optional user comment")


class Feedback(FeedbackBase, table=True):
    """Feedback table model"""

    __tablename__ = "feedback"

    id: UUID = Field(
        default_factory=uuid4, primary_key=True, description="Unique feedback ID"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )


class FeedbackCreate(FeedbackBase):
    """Model for creating feedback"""

    pass


class FeedbackRead(FeedbackBase):
    """Model for reading feedback"""

    id: UUID
    created_at: datetime
