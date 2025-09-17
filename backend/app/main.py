# app/main.py
from time import time
from uuid import uuid4

from fastapi import FastAPI, Request
from sqlmodel import SQLModel

from app.api import query
from app.api.v1 import feedback, health, rag
from app.core.config import settings
from app.core.error_handlers import setup_error_handlers
from app.core.logging import log_api_request, logger
from app.core.metrics import instrumentator
from app.db.session import engine
from app.models import (  # noqa: F401 ensure table registration
    feedback as _feedback_model,
)
from app.models import query as _query_model  # noqa: F401 ensure table registration

# Logging
logger.info("App starting...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI backend for Discord RAG Bot",
)

# Setup error handlers
setup_error_handlers(app)

# Register routers
app.include_router(rag.router)
app.include_router(feedback.router)
app.include_router(query.router, prefix="/api/query")
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])

# Metrics
instrumentator.instrument(app).expose(app)


@app.on_event("startup")
def on_startup():
    logger.info("Application startup - creating database tables")
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created successfully")


@app.on_event("shutdown")
def on_shutdown():
    logger.info("Application shutdown - dropping database tables")
    logger.info("Database tables dropped successfully")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time()
    request_id = str(uuid4())
    user_id = request.headers.get("X-User-ID", "anonymous")

    # Request start logging
    logger.info(
        f"[{request_id}] Request started: {request.method} {request.url.path} \
        | User: {user_id}"
    )

    try:
        response = await call_next(request)
        duration = time() - start_time

        # API request logging (improved logging function)
        log_api_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
            user_id=user_id,
            request_id=request_id,
        )

        return response

    except Exception as e:
        duration = time() - start_time
        logger.error(
            f"[{request_id}] Request failed: {request.method} {request.url.path} \
            | "
            f"User: {user_id} | Duration: {duration:.3f}s | Error: {str(e)}"
        )
        raise
