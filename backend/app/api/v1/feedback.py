"""
Feedback API endpoints
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import logger
from app.services.feedback_service import feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """Request model for submitting feedback"""

    message_id: str
    user_id: str
    score: str  # 'up' or 'down'
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""

    success: bool
    message: str


class FeedbackStatsResponse(BaseModel):
    """Response model for feedback statistics"""

    up: int
    down: int
    total: int


class FeedbackHistoryResponse(BaseModel):
    """Response model for user feedback history"""

    id: str
    message_id: str
    score: str
    comment: Optional[str]
    created_at: str
    question: str
    response: str


class FeedbackSummaryResponse(BaseModel):
    """Response model for feedback summary"""

    total_feedback: int
    up_votes: int
    down_votes: int
    unique_users: int
    unique_messages: int
    satisfaction_rate: float


@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit user feedback for a RAG response

    Args:
        feedback: Feedback data including message_id, user_id, score,
        and optional comment

    Returns:
        Feedback submission result
    """
    try:
        success, message = feedback_service.submit_feedback(
            message_id=feedback.message_id,
            user_id=feedback.user_id,
            score=feedback.score,
            comment=feedback.comment,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return FeedbackResponse(success=success, message=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_feedback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/{message_id}", response_model=FeedbackStatsResponse)
async def get_feedback_stats(message_id: str):
    """
    Get feedback statistics for a specific message

    Args:
        message_id: UUID of the message

    Returns:
        Feedback statistics (up/down counts)
    """
    try:
        stats = feedback_service.get_feedback_stats(message_id)

        return FeedbackStatsResponse(
            up=stats["up"], down=stats["down"], total=stats["up"] + stats["down"]
        )

    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history/{user_id}", response_model=List[FeedbackHistoryResponse])
async def get_user_feedback_history(
    user_id: str,
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of feedback records to return",
    ),
):
    """
    Get feedback history for a specific user

    Args:
        user_id: Discord user ID
        limit: Maximum number of feedback records to return

    Returns:
        List of user's feedback history
    """
    try:
        feedback_list = feedback_service.get_user_feedback(user_id, limit)

        return [
            FeedbackHistoryResponse(
                id=item["id"],
                message_id=item["message_id"],
                score=item["score"],
                comment=item["comment"],
                created_at=item["created_at"],
                question=item["question"],
                response=item["response"],
            )
            for item in feedback_list
        ]

    except Exception as e:
        logger.error(f"Error getting user feedback history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/summary", response_model=FeedbackSummaryResponse)
async def get_feedback_summary(
    days: int = Query(
        default=7, ge=1, le=365, description="Number of days to look back"
    )
):
    """
    Get feedback summary statistics

    Args:
        days: Number of days to look back for statistics

    Returns:
        Feedback summary statistics
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

    except Exception as e:
        logger.error(f"Error getting feedback summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for feedback service

    Returns:
        Service health status
    """
    return {"status": "healthy", "service": "feedback"}
