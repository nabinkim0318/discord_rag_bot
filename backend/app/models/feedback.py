"""
Feedback database models
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class FeedbackBase(SQLModel):
    """Base feedback model"""

    message_id: UUID = Field(
        foreign_key="user_messages.id", description="Reference to user message"
    )
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
