from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ExternalServiceException, RAGException
from app.db.session import get_session
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_enhanced_query_rag_success_conforms_to_response_schema(client):
    """Dict retrieval hits must be converted to List[str] for RAGQueryResponse."""
    with (
        patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
        patch("app.services.enhanced_rag_service.generate_answer") as mock_generate,
    ):
        mock_generate.return_value = (
            "Enhanced RAG answer",
            [
                {
                    "text": "Retrieved context from syllabus.pdf",
                    "chunk_uid": "chunk-1",
                    "source": "syllabus.pdf",
                    "score": 0.91,
                }
            ],
            {"retrieval": {"retrieval_time": 0.02}},
        )

        response = client.post(
            "/api/v1/enhanced-rag/",
            json={"query": "What is the late policy?", "top_k": 3},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Enhanced RAG answer"
    assert data["contexts"] == ["Retrieved context from syllabus.pdf"]
    assert all(isinstance(item, str) for item in data["contexts"])
    assert data["metadata"]["sources"] == ["syllabus.pdf"]
    assert data["metadata"]["uids"] == ["chunk-1"]
    assert data["metadata"]["enhanced_rag"] is True


def test_enhanced_query_rag_failure_returns_sanitized_503(client):
    provider_error = ExternalServiceException(
        "provider secret: invalid credential",
        service_name="llm-provider",
    )

    with (
        patch(
            "app.api.v1.enhanced_rag.run_enhanced_rag_pipeline",
            side_effect=provider_error,
        ),
        patch("app.api.v1.enhanced_rag.record_failure_metric") as mock_failure_metric,
    ):
        response = client.post(
            "/api/v1/enhanced-rag/",
            json={"query": "Trigger enhanced provider failure", "top_k": 3},
        )

    assert response.status_code == 503
    assert "provider secret" not in response.text
    assert "Mock enhanced RAG response" not in response.text
    assert response.json()["message"] == "RAG dependency is temporarily unavailable"
    mock_failure_metric.assert_called_once_with(
        "/api/v1/enhanced-rag/", "EXTERNAL_SERVICE_ERROR"
    )


def test_enhanced_query_rag_pipeline_failure_returns_sanitized_503(client):
    pipeline_error = RAGException(
        "vector store connection refused",
        error_code="RAG_RETRIEVAL_ERROR",
        details={"stage": "retrieval"},
    )

    with (
        patch(
            "app.api.v1.enhanced_rag.run_enhanced_rag_pipeline",
            side_effect=pipeline_error,
        ),
        patch("app.api.v1.enhanced_rag.record_failure_metric") as mock_failure_metric,
    ):
        response = client.post(
            "/api/v1/enhanced-rag/",
            json={"query": "Trigger enhanced retrieval failure", "top_k": 3},
        )

    assert response.status_code == 503
    assert "connection refused" not in response.text
    assert response.json()["stage"] == "retrieval"
    mock_failure_metric.assert_called_once_with(
        "/api/v1/enhanced-rag/", "RAG_RETRIEVAL_ERROR"
    )


def _override_db_session(exec_side_effect=None):
    session = MagicMock()
    if exec_side_effect is not None:
        session.exec.side_effect = exec_side_effect
    else:
        session.exec.return_value = MagicMock()

    def _override():
        yield session

    return _override


def test_enhanced_rag_health_does_not_run_pipeline_or_llm(client):
    app.dependency_overrides[get_session] = _override_db_session()
    try:
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            patch("app.api.v1.enhanced_rag.run_enhanced_rag_pipeline") as mock_pipeline,
            patch("app.api.v1.health.perform_llm_probe") as mock_probe,
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_get_client.return_value = mock_client
            response = client.get("/api/v1/enhanced-rag/health")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["service"] == "enhanced-rag"
    assert payload["mode"] == "readiness"
    mock_pipeline.assert_not_called()
    mock_probe.assert_not_called()


def test_enhanced_rag_health_returns_503_when_not_ready(client):
    sentinel = "SENTINEL_ENHANCED_RAG_HEALTH_DB"
    app.dependency_overrides[get_session] = _override_db_session(Exception(sentinel))
    try:
        with (
            patch("app.api.v1.health.get_weaviate_client") as mock_get_client,
            patch("app.api.v1.enhanced_rag.run_enhanced_rag_pipeline") as mock_pipeline,
        ):
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_get_client.return_value = mock_client
            response = client.get("/api/v1/enhanced-rag/health")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["dependencies"]["database"] == "unhealthy"
    assert sentinel not in response.text
    assert "error" not in payload
    mock_pipeline.assert_not_called()
