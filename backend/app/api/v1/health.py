from time import perf_counter
from typing import Any, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.core.logging import logger
from app.core.metrics import (
    health_check_counter,
    health_check_db_counter,
    health_check_db_failures,
    health_check_db_latency,
    health_check_llm_counter,
    health_check_llm_failures,
    health_check_llm_latency,
    health_check_vector_store_counter,
    health_check_vector_store_failures,
    health_check_vector_store_latency,
)
from app.core.weaviate_client import get_weaviate_client
from app.db.session import get_session

health_router = APIRouter()

PUBLIC_FILESYSTEM_UNAVAILABLE = "filesystem check failed"
PUBLIC_DB_UNAVAILABLE = "database unavailable"
PUBLIC_VECTOR_UNAVAILABLE = "vector store unavailable"
PUBLIC_LLM_PROBE_FAILED = "llm probe failed"


def _json(payload: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(content=payload, status_code=status_code)


def configured_llm_provider() -> Optional[str]:
    if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
        return "azure"
    if settings.OPENAI_API_KEY:
        return "openai"
    return None


def perform_llm_probe() -> None:
    """Tiny opt-in live probe. Tests must mock this and never hit a network."""
    from openai import OpenAI

    timeout = settings.HEALTH_LLM_PROBE_TIMEOUT_SECONDS
    if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        client = OpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            base_url=f"{endpoint}/openai",
            timeout=timeout,
        )
        model = settings.AZURE_OPENAI_DEPLOYMENT or settings.LLM_MODEL
    else:
        client_kwargs: dict[str, Any] = {
            "api_key": settings.OPENAI_API_KEY,
            "timeout": timeout,
        }
        if settings.LLM_API_BASE_URL:
            client_kwargs["base_url"] = settings.LLM_API_BASE_URL
        client = OpenAI(**client_kwargs)
        model = settings.LLM_MODEL

    client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "."}],
        max_tokens=1,
    )


def _check_filesystem() -> tuple[bool, float]:
    start = perf_counter()
    try:
        from app.core.config import get_log_dir

        log_dir = get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        test_file = log_dir / "health_check.tmp"
        test_file.write_text("health_check")
        test_file.unlink()
        return True, perf_counter() - start
    except Exception as exc:
        logger.error("Filesystem health check failed: {}", exc)
        return False, perf_counter() - start


def _record_filesystem(ok: bool) -> None:
    health_check_counter.labels(status="success" if ok else "failure").inc()


def _check_db(session: Session) -> tuple[bool, float]:
    start = perf_counter()
    try:
        session.exec(text("SELECT 1"))
        return True, perf_counter() - start
    except Exception as exc:
        logger.error("Database health check failed: {}", exc)
        return False, perf_counter() - start


def _record_db(ok: bool, duration: float) -> None:
    if ok:
        health_check_db_counter.labels(status="success").inc()
    else:
        health_check_db_counter.labels(status="failure").inc()
        health_check_db_failures.inc()
    health_check_db_latency.observe(duration)


def _check_vector_store() -> tuple[bool, float]:
    start = perf_counter()
    try:
        weaviate_client = get_weaviate_client()
        if weaviate_client is None:
            logger.error("Vector store health check failed: client not available")
            return False, perf_counter() - start
        if weaviate_client.health_check():
            return True, perf_counter() - start
        logger.error("Vector store health check failed: Weaviate not ready")
        return False, perf_counter() - start
    except Exception as exc:
        logger.error("Vector store health check failed: {}", exc)
        return False, perf_counter() - start


def _record_vector_store(ok: bool, duration: float) -> None:
    if ok:
        health_check_vector_store_counter.labels(status="success").inc()
    else:
        health_check_vector_store_counter.labels(status="failure").inc()
        health_check_vector_store_failures.inc()
    health_check_vector_store_latency.observe(duration)


def assess_readiness(session: Session) -> dict[str, Any]:
    """Canonical readiness for a meaningful RAG request.

    Does not record metrics. Callers that own a public probe (/readyz)
    record once; compatibility wrappers must not record again.
    """
    db_ok, db_duration = _check_db(session)
    vector_ok, vector_duration = _check_vector_store()
    ready = db_ok and vector_ok
    return {
        "ready": ready,
        "db_ok": db_ok,
        "db_duration": db_duration,
        "vector_ok": vector_ok,
        "vector_duration": vector_duration,
        "payload": {
            "status": "ready" if ready else "not_ready",
            "dependencies": {
                "database": "healthy" if db_ok else "unhealthy",
                "vector_store": "healthy" if vector_ok else "unhealthy",
            },
            "duration": {
                "database": db_duration,
                "vector_store": vector_duration,
            },
        },
    }


@health_router.get("/")
def health():
    """Process liveness. No external dependency probes. Discord /health uses this."""
    return {"status": "ok"}


@health_router.get("/livez", tags=["Health"])
def livez():
    """Application process liveness. Does not contact DB, Weaviate, or LLM."""
    return {"status": "ok", "mode": "liveness"}


@health_router.get("/readyz", tags=["Health"])
async def readyz(session: Session = Depends(get_session)):
    """Readiness for a meaningful RAG request: database and vector store."""
    result = assess_readiness(session)
    _record_db(result["db_ok"], result["db_duration"])
    _record_vector_store(result["vector_ok"], result["vector_duration"])
    return _json(result["payload"], 200 if result["ready"] else 503)


@health_router.get("/check", tags=["Health"])
async def health_check():
    ok, duration = _check_filesystem()
    _record_filesystem(ok)
    if ok:
        return _json(
            {"status": "healthy", "duration": duration, "checks": ["filesystem"]}
        )
    return _json(
        {
            "status": "unhealthy",
            "error": PUBLIC_FILESYSTEM_UNAVAILABLE,
            "duration": duration,
        },
        503,
    )


@health_router.get("/db", tags=["Health"])
async def health_check_db(session: Session = Depends(get_session)):
    ok, duration = _check_db(session)
    _record_db(ok, duration)
    if ok:
        return _json({"status": "database healthy", "duration": duration})
    return _json(
        {
            "status": "database unhealthy",
            "error": PUBLIC_DB_UNAVAILABLE,
            "duration": duration,
        },
        503,
    )


@health_router.get("/llm", tags=["Health"])
async def health_check_llm():
    """LLM configuration status. Live probes are opt-in and never implied."""
    start = perf_counter()
    provider = configured_llm_provider()
    model = getattr(settings, "LLM_MODEL", "gpt-4o-mini")

    if provider is None:
        duration = perf_counter() - start
        return _json(
            {
                "status": "not_configured",
                "probe": "not_performed",
                "provider": None,
                "model": model,
                "duration": duration,
            }
        )

    if not settings.HEALTH_LLM_PROBE_ENABLED:
        duration = perf_counter() - start
        return _json(
            {
                "status": "configured",
                "probe": "not_performed",
                "provider": provider,
                "model": model,
                "duration": duration,
            }
        )

    try:
        perform_llm_probe()
        duration = perf_counter() - start
        health_check_llm_counter.labels(status="success").inc()
        health_check_llm_latency.observe(duration)
        return _json(
            {
                "status": "healthy",
                "probe": "success",
                "provider": provider,
                "model": model,
                "duration": duration,
                "response_time": duration,
            }
        )
    except Exception as exc:
        duration = perf_counter() - start
        logger.error("LLM live probe failed: {}", exc)
        health_check_llm_counter.labels(status="failure").inc()
        health_check_llm_failures.inc()
        health_check_llm_latency.observe(duration)
        return _json(
            {
                "status": "unhealthy",
                "probe": "failure",
                "provider": provider,
                "model": model,
                "error": PUBLIC_LLM_PROBE_FAILED,
                "duration": duration,
            },
            503,
        )


@health_router.get("/vector-store", tags=["Health"])
async def health_check_vector_store():
    ok, duration = _check_vector_store()
    _record_vector_store(ok, duration)
    if ok:
        return _json(
            {
                "status": "vector store healthy",
                "duration": duration,
                "service": "weaviate",
                "url": settings.WEAVIATE_URL,
            }
        )
    return _json(
        {
            "status": "vector store unhealthy",
            "error": PUBLIC_VECTOR_UNAVAILABLE,
            "duration": duration,
        },
        503,
    )
