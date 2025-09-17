import pytest
from fastapi.testclient import TestClient

from app.main import app


# shared TestClient fixture
@pytest.fixture
def client():
    """shared FastAPI TestClient"""
    return TestClient(app)


# success case test
def test_query_rag_success(client):
    payload = {
        "query": "Explain Retrieval-Augmented Generation",
        "top_k": 3,
        "use_streaming": False,
    }

    response = client.post("/api/v1/rag/", json=payload)
    assert response.status_code == 200

    data = response.json()

    assert "answer" in data
    assert isinstance(data["answer"], str)

    assert "contexts" in data
    assert isinstance(data["contexts"], list)
    assert len(data["contexts"]) > 0

    assert "metadata" in data
    metadata = data["metadata"]
    for key in ["pipeline_runtime_ms", "retriever", "generator", "timestamp"]:
        assert key in metadata


# failure cases parametrize
@pytest.mark.parametrize(
    "payload, expected_status",
    [
        ({"top_k": 3, "use_streaming": False}, 422),  # query is missing
        (
            {
                "query": "Explain RAG",
                "top_k": "not_a_number",
                "use_streaming": False,
            },  # invalid top_k
            422,
        ),
        ({"query": "Another test", "top_k": -5}, 422),  # negative top_k
    ],
)
def test_query_rag_failure_cases(client, payload, expected_status):
    response = client.post("/api/v1/rag/", json=payload)
    assert response.status_code == expected_status
    data = response.json()
    assert "detail" in data
