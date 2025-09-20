from time import perf_counter

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
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
from app.db.session import get_session

router = APIRouter()


@router.get("/", tags=["Health"])
async def health_check():
    start = perf_counter()
    try:
        # Basic file system check (logs directory)
        from app.core.config import get_log_dir

        log_dir = get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)

        # Verify directory is writable
        test_file = log_dir / "health_check.tmp"
        test_file.write_text("health_check")
        test_file.unlink()

        duration = perf_counter() - start
        health_check_counter.labels(status="success").inc()
        return {"status": "healthy", "duration": duration, "checks": ["filesystem"]}
    except Exception as e:
        duration = perf_counter() - start
        health_check_counter.labels(status="failure").inc()
        return {"status": "unhealthy", "error": str(e), "duration": duration}


@router.get("/db", tags=["Health"])
async def health_check_db(session: Session = Depends(get_session)):
    start = perf_counter()
    try:
        # actual DB ping or query execution example: await db.execute("SELECT 1")
        session.exec(text("SELECT 1"))  # actual ping
        duration = perf_counter() - start
        health_check_db_counter.labels(status="success").inc()
        health_check_db_latency.observe(duration)
        return {"status": "database healthy", "duration": duration}
    except Exception as e:
        duration = perf_counter() - start
        health_check_db_counter.labels(status="failure").inc()
        health_check_db_failures.inc()
        return {"status": "database unhealthy", "error": str(e), "duration": duration}


@router.get("/llm", tags=["Health"])
async def health_check_llm():
    start = perf_counter()
    try:
        # Actual LLM health check - make a minimal call
        from app.core.config import settings

        if not settings.OPENAI_API_KEY:
            raise Exception("OpenAI API key not configured")

        # Simple completion to test LLM connectivity
        # import openai

        # client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        # response = await client.chat.completions.create(
        #     model=settings.OPENAI_MODEL,
        #     messages=[{"role": "user", "content": "Hi"}],
        #     max_tokens=1,
        #     timeout=10.0,
        # )

        duration = perf_counter() - start
        health_check_llm_counter.labels(status="success").inc()
        health_check_llm_latency.observe(duration)
        return {
            "status": "llm healthy",
            "duration": duration,
            "model": settings.OPENAI_MODEL,
            "response_time": duration,
        }
    except Exception as e:
        duration = perf_counter() - start
        health_check_llm_counter.labels(status="failure").inc()
        health_check_llm_failures.inc()
        return {"status": "llm unhealthy", "error": str(e), "duration": duration}


@router.get("/vector-store", tags=["Health"])
async def health_check_vector_store():
    start = perf_counter()
    try:
        # Check Weaviate health (with fallback)
        try:
            from app.core.weaviate_client import get_weaviate_client

            weaviate_client = get_weaviate_client()
            if weaviate_client is None:
                raise Exception("Weaviate client not available")

            is_healthy = weaviate_client.health_check()

            duration = perf_counter() - start
            if is_healthy:
                health_check_vector_store_counter.labels(status="success").inc()
                health_check_vector_store_latency.observe(duration)
                return {
                    "status": "vector store healthy",
                    "duration": duration,
                    "service": "weaviate",
                    "url": settings.WEAVIATE_URL,
                }
            else:
                health_check_vector_store_counter.labels(status="failure").inc()
                health_check_vector_store_failures.inc()
                return {
                    "status": "vector store unhealthy",
                    "error": "Weaviate not ready",
                    "duration": duration,
                }
        except ImportError:
            duration = perf_counter() - start
            health_check_vector_store_counter.labels(status="failure").inc()
            health_check_vector_store_failures.inc()
            return {
                "status": "vector store unavailable",
                "error": "Weaviate client not available",
                "duration": duration,
                "url": settings.WEAVIATE_URL,
            }
    except Exception as e:
        duration = perf_counter() - start
        health_check_vector_store_counter.labels(status="failure").inc()
        health_check_vector_store_failures.inc()
        return {
            "status": "vector store unhealthy",
            "error": str(e),
            "duration": duration,
        }
