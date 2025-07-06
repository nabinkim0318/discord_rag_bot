from app.api.v1 import feedback, rag
from app.core.logging import logger
from fastapi import FastAPI, Request

app = FastAPI(title="RAG API")
app.include_router(rag.router)
app.include_router(feedback.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        raise
