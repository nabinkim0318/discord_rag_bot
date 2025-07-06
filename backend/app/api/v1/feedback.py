from app.models.feedback import FeedbackRequest, FeedbackResponse
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    # TODO: actual save logic (ex. DB, file save, etc.)
    return {"status": "success", "message": "Feedback received. Thank you!"}
