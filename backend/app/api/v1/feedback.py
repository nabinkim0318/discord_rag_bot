from app.models.feedback import FeedbackRequest, FeedbackResponse
from fastapi import APIRouter
from loguru import logger

router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    logger.info(f"Received feedback: {feedback}")
    return {"status": "success", "message": "Feedback received. Thank you!"}
