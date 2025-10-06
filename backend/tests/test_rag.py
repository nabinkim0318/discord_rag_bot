from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_query_rag_success(client):
    with patch("app.api.v1.rag.run_rag_pipeline") as mock_rag_pipeline:
        # Mock the RAG pipeline response
        # Note: contexts should be a list of strings based on RAGQueryResponse model
        mock_rag_pipeline.return_value = (
            "Retrieval-Augmented Generation (RAG) is a technique that combines retrieval and generation to improve AI responses.",
            [
                "RAG combines retrieval and generation from test_doc.pdf",
            ],
            {
                "retrieval_time": 0.1,
                "generation_time": 0.5,
                "total_time": 0.6,
            },
        )

        payload = {
            "query": "What is Retrieval-Augmented Generation?",
            "top_k": 3,
            "use_streaming": False,
        }

        response = client.post("/api/v1/rag/", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data.get("answer"), str)
        assert isinstance(data.get("contexts"), list)
        assert len(data["contexts"]) > 0
        assert isinstance(data.get("metadata"), dict)


# @pytest.mark.parametrize(
#     "payload, expected_status",
#     [
#         ({"top_k": 3, "use_streaming": False}, 422),  # query is missing
#         ({"query": "test", "top_k": "not_a_number"}, 422),  # invalid type
#         ({"query": "test", "top_k": -1}, 422),  # out of range
#     ],
# )

# def test_query_rag_failure_cases(client, payload, expected_status):
#     # response = client.post("/api/v1/rag/", json=payload)
#     # assert response.status_code == expected_status
#     # data = response.json()
#     # # Check for new error response format
#     # assert "error" in data
#     # assert "error_code" in data
#     # assert "message" in data
