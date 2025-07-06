from time import time
from uuid import uuid4

from app.api.v1 import feedback, rag
from app.core.logging import logger
from app.core.metrics import instrumentator
from fastapi import FastAPI, Request

# Logging
logger.info("App starting...")

app = FastAPI(title="RAG API")
app.include_router(rag.router)
app.include_router(feedback.router)

# Metrics
instrumentator.instrument(app).expose(app)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time()

    # Generate a unique request ID (optional)
    request_id = str(uuid4())

    # Assume: User ID is received from header
    user_id = request.headers.get("X-User-ID", "anonymous")
    query_path = request.url.path

    logger.info(
        f"[{request_id}] Received request: user_id={user_id}, "
        f"path={query_path}, method={request.method}"
    )

    try:
        response = await call_next(request)
        duration = time() - start_time
        logger.info(
            f"[{request_id}] Request completed: user_id={user_id}, "
            f"path={query_path}, method={request.method}, "
            f"status={response.status_code}, duration={duration:.2f}s"
        )

        return response
    except Exception as e:
        duration = time() - start_time
        logger.exception(
            f"[{request_id}] Unhandled error: user_id={user_id}, "
            f"path={query_path}, method={request.method}, status=500, "
            f"duration={duration:.2f}s, error={e}"
        )
        raise
