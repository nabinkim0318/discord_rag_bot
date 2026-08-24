# app/main.py
from contextlib import asynccontextmanager
from pathlib import Path
from time import time
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import query
from app.api.v1 import enhanced_rag, feedback, health, rag
from app.core.config import settings
from app.core.error_handlers import setup_error_handlers
from app.core.logging import log_api_request, logger
from app.core.metrics import instrumentator
from app.core.request_id import canonical_request_id
from app.db.schema import apply_schema
from app.db.session import engine
from app.models import (  # noqa: F401 ensure table registration
    feedback as _feedback_model,
)
from app.models import query as _query_model  # noqa: F401 ensure table registration

# Load environment variables from root .env file
root_dir = Path(__file__).parent.parent.parent
env_path = root_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Logging
logger.info("App starting...")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    # Startup — Alembic is the runtime schema authority
    logger.info("Application startup - applying Alembic migrations")
    apply_schema(engine)
    logger.info("Database schema is up to date")

    yield

    # Shutdown
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI backend for Discord RAG Bot",
    lifespan=lifespan,
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
app.include_router(rag.rag_router)
app.include_router(enhanced_rag.enhanced_rag_router)
app.include_router(feedback.feedback_router)
app.include_router(query.query_router, prefix="/api/query")
app.include_router(health.health_router, prefix="/api/v1/health", tags=["Health"])

# Metrics - properly configure instrumentator
if settings.METRICS_ENABLED:
    instrumentator.instrument(app).expose(app, endpoint=settings.METRICS_PATH)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time()
    request_id = canonical_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id

    logger.bind(request_id=request_id).info(
        f"Request started: {request.method} {request.url.path} "
        f"| RequestID: {request_id}"
    )

    try:
        response = await call_next(request)
        duration = time() - start_time
        response.headers["X-Request-ID"] = request_id

        log_api_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
            request_id=request_id,
        )

        return response

    except Exception as exc:
        duration = time() - start_time
        logger.bind(request_id=request_id).error(
            f"Request failed: {request.method} {request.url.path} "
            f"| Duration: {duration:.3f}s | ErrorType: {type(exc).__name__}"
        )
        raise
