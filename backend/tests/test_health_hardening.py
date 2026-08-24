"""Regression tests for liveness, readiness, and health sanitization."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.v1.health import (
    PUBLIC_DB_UNAVAILABLE,
    PUBLIC_LLM_PROBE_FAILED,
    PUBLIC_VECTOR_UNAVAILABLE,
)
from app.core.metrics import (
    health_check_db_counter,
    health_check_db_failures,
    health_check_llm_counter,
    health_check_llm_failures,
    health_check_vector_store_counter,
    health_check_vector_store_failures,
)
from app.db.session import get_session
from app.main import app

SENTINEL_DB = "SENTINEL_INTERNAL_DB_ERROR"
SENTINEL_VECTOR = "SENTINEL_INTERNAL_VECTOR_ERROR"
SENTINEL_LLM = "SENTINEL_INTERNAL_LLM_ERROR"


def _counter_value(counter, **labels) -> float:
    if labels:
        return counter.labels(**labels)._value.get()
    return counter._value.get()


def _override_db_session(exec_side_effect=None):
    session = MagicMock()
    if exec_side_effect is not None:
        session.exec.side_effect = exec_side_effect
    else:
        session.exec.return_value = MagicMock()

    def _override():
        yield session

    return session, _override


def test_livez_returns_200_without_external_dependencies():
    with (
        patch("app.api.v1.health._check_db") as mock_db,
        patch("app.api.v1.health._check_vector_store") as mock_vector,
        patch("app.api.v1.health.perform_llm_probe") as mock_probe,
        patch("app.api.v1.health.get_weaviate_client") as mock_client,
        TestClient(app) as client,
    ):
        response = client.get("/api/v1/health/livez")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["mode"] == "liveness"
    mock_db.assert_not_called()
    mock_vector.assert_not_called()
    mock_probe.assert_not_called()
    mock_client.assert_not_called()


def test_readyz_returns_200_when_critical_dependencies_are_healthy():
    _, override = _override_db_session()
    app.dependency_overrides[get_session] = override
    try:
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            TestClient(app) as client,
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_get_client.return_value = mock_client
            response = client.get("/api/v1/health/readyz")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["dependencies"]["database"] == "healthy"
    assert payload["dependencies"]["vector_store"] == "healthy"


def test_readyz_returns_503_when_db_unavailable():
    _, override = _override_db_session(Exception(SENTINEL_DB))
    app.dependency_overrides[get_session] = override
    try:
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            TestClient(app) as client,
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_get_client.return_value = mock_client
            response = client.get("/api/v1/health/readyz")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["dependencies"]["database"] == "unhealthy"
    assert SENTINEL_DB not in response.text


def test_readyz_returns_503_when_vector_store_unavailable():
    _, override = _override_db_session()
    app.dependency_overrides[get_session] = override
    try:
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            TestClient(app) as client,
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = False
            mock_get_client.return_value = mock_client
            response = client.get("/api/v1/health/readyz")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["dependencies"]["vector_store"] == "unhealthy"


def test_db_returns_503_on_failure_without_raw_exception():
    _, override = _override_db_session(Exception(SENTINEL_DB))
    app.dependency_overrides[get_session] = override
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/health/db")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "database unhealthy"
    assert payload["error"] == PUBLIC_DB_UNAVAILABLE
    assert SENTINEL_DB not in response.text


def test_vector_store_returns_503_when_unhealthy_without_raw_exception():
    with (
        patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
        TestClient(app) as client,
    ):
        mock_get_client.side_effect = RuntimeError(SENTINEL_VECTOR)
        response = client.get("/api/v1/health/vector-store")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "vector store unhealthy"
    assert payload["error"] == PUBLIC_VECTOR_UNAVAILABLE
    assert SENTINEL_VECTOR not in response.text


def test_llm_does_not_report_successful_live_check_when_no_probe_occurred():
    before_success = _counter_value(health_check_llm_counter, status="success")
    with (
        patch("app.api.v1.health.settings") as mock_settings,
        patch("app.api.v1.health.perform_llm_probe") as mock_probe,
        TestClient(app) as client,
    ):
        mock_settings.OPENAI_API_KEY = "present"
        mock_settings.AZURE_OPENAI_API_KEY = None
        mock_settings.AZURE_OPENAI_ENDPOINT = None
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.HEALTH_LLM_PROBE_ENABLED = False
        response = client.get("/api/v1/health/llm")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "configured"
    assert payload["probe"] == "not_performed"
    assert payload["status"] != "llm healthy"
    mock_probe.assert_not_called()
    assert _counter_value(health_check_llm_counter, status="success") == before_success


def test_optional_llm_probe_success_is_mocked_and_never_hits_network():
    before_success = _counter_value(health_check_llm_counter, status="success")
    with (
        patch("app.api.v1.health.settings") as mock_settings,
        patch("app.api.v1.health.perform_llm_probe") as mock_probe,
        TestClient(app) as client,
    ):
        mock_settings.OPENAI_API_KEY = "present"
        mock_settings.AZURE_OPENAI_API_KEY = None
        mock_settings.AZURE_OPENAI_ENDPOINT = None
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.HEALTH_LLM_PROBE_ENABLED = True
        mock_probe.return_value = None
        response = client.get("/api/v1/health/llm")

    assert response.status_code == 200
    payload = response.json()
    assert payload["probe"] == "success"
    assert payload["status"] == "healthy"
    mock_probe.assert_called_once()
    assert (
        _counter_value(health_check_llm_counter, status="success") == before_success + 1
    )


def test_optional_llm_probe_failure_is_truthful_and_sanitized():
    before_failure = _counter_value(health_check_llm_counter, status="failure")
    before_failures = _counter_value(health_check_llm_failures)
    with (
        patch("app.api.v1.health.settings") as mock_settings,
        patch("app.api.v1.health.perform_llm_probe") as mock_probe,
        TestClient(app) as client,
    ):
        mock_settings.OPENAI_API_KEY = "present"
        mock_settings.AZURE_OPENAI_API_KEY = None
        mock_settings.AZURE_OPENAI_ENDPOINT = None
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.HEALTH_LLM_PROBE_ENABLED = True
        mock_probe.side_effect = RuntimeError(SENTINEL_LLM)
        response = client.get("/api/v1/health/llm")

    assert response.status_code == 503
    payload = response.json()
    assert payload["probe"] == "failure"
    assert payload["status"] == "unhealthy"
    assert payload["error"] == PUBLIC_LLM_PROBE_FAILED
    assert SENTINEL_LLM not in response.text
    assert (
        _counter_value(health_check_llm_counter, status="failure") == before_failure + 1
    )
    assert _counter_value(health_check_llm_failures) == before_failures + 1


def test_db_success_and_failure_metrics_follow_result():
    before_success = _counter_value(health_check_db_counter, status="success")
    before_failure = _counter_value(health_check_db_counter, status="failure")
    before_failures = _counter_value(health_check_db_failures)

    _, healthy = _override_db_session()
    app.dependency_overrides[get_session] = healthy
    try:
        with TestClient(app) as client:
            ok = client.get("/api/v1/health/db")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert ok.status_code == 200
    assert (
        _counter_value(health_check_db_counter, status="success") == before_success + 1
    )
    assert _counter_value(health_check_db_counter, status="failure") == before_failure

    _, unhealthy = _override_db_session(Exception(SENTINEL_DB))
    app.dependency_overrides[get_session] = unhealthy
    try:
        with TestClient(app) as client:
            failed = client.get("/api/v1/health/db")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert failed.status_code == 503
    assert (
        _counter_value(health_check_db_counter, status="success") == before_success + 1
    )
    assert (
        _counter_value(health_check_db_counter, status="failure") == before_failure + 1
    )
    assert _counter_value(health_check_db_failures) == before_failures + 1


def test_vector_store_metrics_follow_result():
    before_success = _counter_value(health_check_vector_store_counter, status="success")
    before_failure = _counter_value(health_check_vector_store_counter, status="failure")
    before_failures = _counter_value(health_check_vector_store_failures)

    with (
        patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
        TestClient(app) as client,
    ):
        mock_client = MagicMock()
        mock_client.health_check.return_value = True
        mock_get_client.return_value = mock_client
        ok = client.get("/api/v1/health/vector-store")

        mock_client.health_check.return_value = False
        failed = client.get("/api/v1/health/vector-store")

    assert ok.status_code == 200
    assert failed.status_code == 503
    assert (
        _counter_value(health_check_vector_store_counter, status="success")
        == before_success + 1
    )
    assert (
        _counter_value(health_check_vector_store_counter, status="failure")
        == before_failure + 1
    )
    assert _counter_value(health_check_vector_store_failures) == before_failures + 1


def test_readyz_records_dependency_metrics_once_per_check():
    before_db_success = _counter_value(health_check_db_counter, status="success")
    before_vector_success = _counter_value(
        health_check_vector_store_counter, status="success"
    )

    _, override = _override_db_session()
    app.dependency_overrides[get_session] = override
    try:
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            TestClient(app) as client,
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_get_client.return_value = mock_client
            response = client.get("/api/v1/health/readyz")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200
    assert (
        _counter_value(health_check_db_counter, status="success")
        == before_db_success + 1
    )
    assert (
        _counter_value(health_check_vector_store_counter, status="success")
        == before_vector_success + 1
    )


def test_docker_liveness_url_exists_and_returns_intended_status():
    with TestClient(app) as client:
        response = client.get("/api/v1/health/livez")
    assert response.status_code == 200
    assert response.json()["mode"] == "liveness"


def test_enhanced_rag_health_matches_readyz_without_double_counting_metrics():
    before_db_success = _counter_value(health_check_db_counter, status="success")
    before_vector_success = _counter_value(
        health_check_vector_store_counter, status="success"
    )
    before_db_failure = _counter_value(health_check_db_counter, status="failure")

    _, override = _override_db_session()
    app.dependency_overrides[get_session] = override
    try:
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            patch("app.api.v1.enhanced_rag.run_enhanced_rag_pipeline") as mock_pipeline,
            TestClient(app) as client,
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_get_client.return_value = mock_client
            ok = client.get("/api/v1/enhanced-rag/health")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert ok.status_code == 200
    assert ok.json()["status"] == "ready"
    assert ok.json()["service"] == "enhanced-rag"
    mock_pipeline.assert_not_called()
    assert (
        _counter_value(health_check_db_counter, status="success") == before_db_success
    )
    assert (
        _counter_value(health_check_vector_store_counter, status="success")
        == before_vector_success
    )

    _, unhealthy = _override_db_session(Exception(SENTINEL_DB))
    app.dependency_overrides[get_session] = unhealthy
    try:
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            TestClient(app) as client,
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_get_client.return_value = mock_client
            failed = client.get("/api/v1/enhanced-rag/health")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert failed.status_code == 503
    assert failed.json()["status"] == "not_ready"
    assert SENTINEL_DB not in failed.text
    assert (
        _counter_value(health_check_db_counter, status="failure") == before_db_failure
    )


def test_enhanced_rag_health_returns_503_when_vector_store_unavailable():
    _, override = _override_db_session()
    app.dependency_overrides[get_session] = override
    try:
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            TestClient(app) as client,
        ):
            mock_get_client.side_effect = RuntimeError(SENTINEL_VECTOR)
            response = client.get("/api/v1/enhanced-rag/health")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["dependencies"]["vector_store"] == "unhealthy"
    assert SENTINEL_VECTOR not in response.text
