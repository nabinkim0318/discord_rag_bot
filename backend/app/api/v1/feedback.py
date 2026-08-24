"""
Feedback API endpoints
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.exceptions import DatabaseException
from app.core.logging import logger
from app.services.feedback_service import feedback_service

feedback_router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

WEB_FEEDBACK_USER_ID = "web"


class FeedbackRequest(BaseModel):
    """Request model for submitting feedback"""

    model_config = ConfigDict(populate_by_name=True)

    query_id: str = Field(alias="message_id")  # Using alias for API compatibility
    user_id: Optional[str] = Field(
        default=WEB_FEEDBACK_USER_ID,
        max_length=128,
        description=(
            "Caller-supplied feedback identity for duplicate detection. "
            "Not authentication. Web clients may omit this; Discord sends "
            "the Discord user id."
        ),
    )
    score: str  # 'up' or 'down'
    comment: Optional[str] = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""

    success: bool
    message: str


class FeedbackStatsResponse(BaseModel):
    """Response model for feedback statistics"""

    up: int
    down: int
    total: int


class FeedbackSummaryResponse(BaseModel):
    """Response model for feedback summary"""

    total_feedback: int
    up_votes: int
    down_votes: int
    unique_users: int
    unique_messages: int
    satisfaction_rate: float


@feedback_router.post("/submit", response_model=FeedbackResponse)
def submit_feedback(feedback: FeedbackRequest):
    """
    Submit user feedback for a RAG response
    """
    try:
        success, message = feedback_service.submit_feedback(
            query_id=feedback.query_id,
            user_id=feedback.user_id or WEB_FEEDBACK_USER_ID,
            score=feedback.score,
            comment=feedback.comment,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return FeedbackResponse(success=success, message=message)

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error in submit_feedback")
        raise DatabaseException(
            message="Feedback submission failed",
            error_code="FEEDBACK_SUBMISSION_ERROR",
            details={"service": "feedback_service"},
        )


@feedback_router.get("/stats/{query_id}", response_model=FeedbackStatsResponse)
def get_feedback_stats(query_id: str):
    """
    Get aggregate feedback counts for a specific query.
    Does not return prompts, answers, or user identifiers.
    """
    try:
        stats = feedback_service.get_feedback_stats(query_id)

        return FeedbackStatsResponse(
            up=stats["up"], down=stats["down"], total=stats["up"] + stats["down"]
        )

    except Exception:
        logger.exception("Error getting feedback stats")
        raise HTTPException(status_code=500, detail="Internal server error")


@feedback_router.get("/summary", response_model=FeedbackSummaryResponse)
def get_feedback_summary(
    days: int = Query(
        default=7, ge=1, le=365, description="Number of days to look back"
    ),
):
    """
    Get aggregate feedback summary statistics.
    Does not return prompts, answers, or user identifiers.
    """
    try:
        summary = feedback_service.get_feedback_summary(days)

        return FeedbackSummaryResponse(
            total_feedback=summary["total_feedback"],
            up_votes=summary["up_votes"],
            down_votes=summary["down_votes"],
            unique_users=summary["unique_users"],
            unique_messages=summary["unique_messages"],
            satisfaction_rate=summary["satisfaction_rate"],
        )

    except Exception:
        logger.exception("Error getting feedback summary")
        raise HTTPException(status_code=500, detail="Internal server error")


@feedback_router.get("/health")
def health_check():
    """
    Health check endpoint for feedback service
    """
    return {"status": "healthy", "service": "feedback"}
