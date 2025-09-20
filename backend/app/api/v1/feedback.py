# app/api/v1/feedback.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.core.logging import logger
from app.core.metrics import record_feedback_metric
from app.db.session import get_session
from app.models.feedback import Feedback, FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    session: Session = Depends(get_session),
    http_request: Request = None,
):
    """
    Submit feedback and save to database
    """
    try:
        # Extract request context
        request_id = None
        user_id = None
        try:
            if http_request is not None:
                request_id = http_request.headers.get("X-Request-ID")
                user_id = http_request.headers.get("X-User-ID")
        except Exception:
            pass

        if not user_id:
            raise HTTPException(status_code=400, detail="X-User-ID header required")

        logger.info(
            "Received feedback: {} for query: {}",
            feedback.feedback_type,
            feedback.query_id,
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "query_id": feedback.query_id,
            },
        )

        # Save feedback to database
        feedback_record = Feedback(
            query_id=feedback.query_id,
            user_id=user_id,
            feedback=feedback.feedback_type,
            comment=feedback.comment,
        )

        session.add(feedback_record)
        session.commit()
        session.refresh(feedback_record)

        # Record metric
        record_feedback_metric(feedback.feedback_type)

        logger.info(
            "Feedback saved to database with ID: {}",
            feedback_record.id,
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "feedback_id": feedback_record.id,
                "query_id": feedback.query_id,
            },
        )

        return {
            "status": "success",
            "message": "Feedback received. Thank you!",
            "feedback_id": feedback_record.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save feedback: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to save feedback: {str(e)}"
        )
