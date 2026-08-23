from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ExternalServiceException, RAGException
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
