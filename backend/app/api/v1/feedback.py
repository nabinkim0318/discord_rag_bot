# app/api/v1/feedback.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.logging import logger
from app.core.metrics import record_feedback_metric
from app.db.session import get_session
from app.models.feedback import Feedback, FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest, session: Session = Depends(get_session)
):
    """
    Submit feedback and save to database
    """
    try:
        logger.info(
            f"Received feedback: {feedback.feedback_type} "
            f"for query: {feedback.query_id}"
        )

        # Save feedback to database
        feedback_record = Feedback(
            query_id=feedback.query_id,
            feedback=feedback.feedback_type,
            comment=feedback.comment,
        )

        session.add(feedback_record)
        session.commit()
        session.refresh(feedback_record)

        # Record metric
        record_feedback_metric(feedback.feedback_type)

        logger.info(f"Feedback saved to database with ID: {feedback_record.id}")

        return {
            "status": "success",
            "message": "Feedback received. Thank you!",
            "feedback_id": feedback_record.id,
        }

    except Exception as e:
        logger.error(f"Failed to save feedback: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to save feedback: {str(e)}"
        )
