from time import perf_counter

from fastapi import APIRouter

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

router = APIRouter()


@router.get("/", tags=["Health"])
async def health_check():
    start = perf_counter()
    try:
        # insert the simple internal check logic here (e.g. file access)
        duration = perf_counter() - start
        health_check_counter.labels(status="success").inc()
        return {"status": "healthy", "duration": duration}
    except Exception as e:
        duration = perf_counter() - start
        health_check_counter.labels(status="failure").inc()
        return {"status": "unhealthy", "error": str(e), "duration": duration}


@router.get("/db", tags=["Health"])
async def health_check_db():
    start = perf_counter()
    try:
        # actual DB ping or query execution example: await db.execute("SELECT 1")
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
        # LLM call example: await llm.call("health check")
        duration = perf_counter() - start
        health_check_llm_counter.labels(status="success").inc()
        health_check_llm_latency.observe(duration)
        return {"status": "llm healthy", "duration": duration}
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
            from app.core.weaviate_client import weaviate_client

            is_healthy = weaviate_client.health_check()

            duration = perf_counter() - start
            if is_healthy:
                health_check_vector_store_counter.labels(status="success").inc()
                health_check_vector_store_latency.observe(duration)
                return {
                    "status": "vector store healthy",
                    "duration": duration,
                    "service": "weaviate",
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
