# app/main.py
from time import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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

# Setup CORS - fix wildcard + credentials conflict
allow_origins = settings.CORS_ORIGINS.copy()
allow_credentials = settings.CORS_ALLOW_CREDENTIALS

# Remove wildcard if credentials are enabled
if allow_credentials and "*" in allow_origins:
    allow_origins = [o for o in allow_origins if o != "*"]
    # Only allow credentials if we have specific origins
    allow_credentials = bool(allow_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(rag.router)
# app.include_router(enhanced_rag.router)  # Disabled for now
app.include_router(feedback.router)
app.include_router(query.router, prefix="/api/query")
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])

# Metrics - properly configure instrumentator
if settings.METRICS_ENABLED:
    instrumentator.instrument(app).expose(app, endpoint=settings.METRICS_PATH)


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
    channel_id = request.headers.get("X-Channel-ID", "unknown")

    # Request start logging
    logger.bind(request_id=request_id, user_id=user_id, channel_id=channel_id).info(
        f"Request started: {request.method} {request.url.path} \
        | User: {user_id} | Channel: {channel_id} | RequestID: {request_id}"
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
            channel_id=channel_id,
            request_id=request_id,
        )

        return response

    except Exception as e:
        duration = time() - start_time
        logger.bind(
            request_id=request_id, user_id=user_id, channel_id=channel_id
        ).error(
            f"Request failed: {request.method} {request.url.path} \
            | User: {user_id} | Channel: {channel_id} | Duration: {duration:.3f}s \
            | Error: {str(e)}"
        )
        raise
