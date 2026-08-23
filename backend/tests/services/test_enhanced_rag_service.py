"""
Tests for Enhanced RAG service functionality
"""

from unittest.mock import patch

import pytest
from rag_mocks import mock_enhanced_rag_pipeline

from app.core.exceptions import RAGException
from app.services import enhanced_rag_service as enhanced_rag_module
from app.services.enhanced_rag_service import run_enhanced_rag_pipeline


class TestEnhancedRAGService:
    """Test cases for enhanced RAG service functionality"""

    def test_mock_enhanced_rag_pipeline(self):
        """Test the mock enhanced RAG pipeline"""
        query = "Test enhanced query"
        answer, contexts, metadata = mock_enhanced_rag_pipeline(query)

        assert "Mock enhanced RAG response" in answer
        assert len(contexts) == 1
        assert contexts[0] == "Mock context for: Test enhanced query"
        assert metadata["mock"] is True
        assert metadata["pipeline"] == "mock_enhanced_rag"

    def test_run_enhanced_rag_pipeline_with_rag_agent(self):
        """Test enhanced RAG pipeline with RAG agent available"""
        query = "Test enhanced query"

        # Mock RAG agent available and generate_answer function
        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch("app.services.enhanced_rag_service.generate_answer") as mock_generate,
        ):
            mock_generate.return_value = (
                "Enhanced answer from RAG agent",
                [
                    {
                        "text": "Enhanced context",
                        "chunk_uid": "id1",
                        "source": "doc1.pdf",
                        "score": 0.9,
                    }
                ],
                {"retrieval": {"retrieval_time": 0.03}},
            )

            answer, contexts, metadata = run_enhanced_rag_pipeline(query)

            assert answer == "Enhanced answer from RAG agent"
            assert len(contexts) == 1
            assert contexts[0] == "Enhanced context"
            assert metadata["enhanced_rag"] is True
            assert metadata["sources"] == ["doc1.pdf"]
            assert metadata["uids"] == ["id1"]
            assert "total_time" in metadata
            mock_generate.assert_called_once()

    def test_run_enhanced_rag_pipeline_without_rag_agent(self):
        """Test enhanced RAG pipeline without RAG agent"""
        query = "Test enhanced query"

        with patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", False):
            with pytest.raises(RAGException) as exc_info:
                run_enhanced_rag_pipeline(query)

        assert exc_info.value.error_code == "RAG_DEPENDENCY_UNAVAILABLE"
        assert exc_info.value.details["stage"] == "initialization"

    def test_run_enhanced_rag_pipeline_exception_handling(self):
        """Test enhanced RAG pipeline exception propagation without fallback"""
        query = "Failing query"

        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch(
                "app.services.enhanced_rag_service.generate_answer",
                side_effect=Exception("RAG error"),
            ),
            patch("app.services.enhanced_rag_service.log_rag_operation") as mock_log,
            patch("app.services.enhanced_rag_service.record_retrieval_hit") as mock_hit,
        ):
            with pytest.raises(RAGException) as exc_info:
                run_enhanced_rag_pipeline(query)

        assert exc_info.value.error_code == "ENHANCED_RAG_PIPELINE_ERROR"
        assert "RAG error" not in exc_info.value.message
        assert mock_log.call_args.args[1] is False
        mock_hit.assert_not_called()

    def test_run_enhanced_rag_pipeline_with_user_context(self):
        """Test enhanced RAG pipeline with user context"""
        query = "Test query with context"
        user_id = "user123"
        channel_id = "channel456"
        request_id = "req789"

        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch("app.services.enhanced_rag_service.generate_answer") as mock_generate,
        ):
            mock_generate.return_value = (
                "Contextual answer",
                [
                    {
                        "text": "Contextual context",
                        "chunk_uid": "id1",
                        "source": "doc1.pdf",
                        "score": 0.8,
                    }
                ],
                {"retrieval": {"retrieval_time": 0.02}},
            )

            answer, contexts, metadata = run_enhanced_rag_pipeline(
                query, user_id=user_id, channel_id=channel_id, request_id=request_id
            )

            assert answer == "Contextual answer"
            assert len(contexts) == 1
            assert metadata["enhanced_rag"] is True
            mock_generate.assert_called_once()

    def test_run_enhanced_rag_pipeline_custom_parameters(self):
        """Test enhanced RAG pipeline with custom parameters"""
        query = "Test query with custom params"

        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch("app.services.enhanced_rag_service.generate_answer") as mock_generate,
        ):
            mock_generate.return_value = (
                "Custom answer",
                [
                    {
                        "text": "Custom context",
                        "chunk_uid": "id1",
                        "source": "doc1.pdf",
                        "score": 0.7,
                    }
                ],
                {"retrieval": {"retrieval_time": 0.01}},
            )

            answer, contexts, metadata = run_enhanced_rag_pipeline(
                query,
                top_k=3,
                user_id="test_user",
                channel_id="test_channel",
                request_id="test_request",
            )

            assert answer == "Custom answer"
            assert metadata["enhanced_rag"] is True
            mock_generate.assert_called_once()

    def test_run_enhanced_rag_pipeline_context_formatting(self):
        """Test enhanced RAG pipeline context formatting"""
        query = "Test context formatting"

        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch("app.services.enhanced_rag_service.generate_answer") as mock_generate,
        ):
            # Mock response with various context formats
            mock_generate.return_value = (
                "Formatted answer",
                [
                    {
                        "text": "Context 1",
                        "chunk_uid": "id1",
                        "source": "doc1.pdf",
                        "score": 0.9,
                    },
                    {
                        "text": "Context 2",
                        "chunk_uid": "id2",
                        "source": "doc2.pdf",
                        "score": 0.8,
                    },
                    {
                        "content": "Context 3",
                        "chunk_uid": "id3",
                        "source": "doc3.pdf",
                        "score": 0.7,
                    },
                ],
                {"retrieval": {"retrieval_time": 0.03}},
            )

            answer, contexts, metadata = run_enhanced_rag_pipeline(query)

            assert answer == "Formatted answer"
            assert len(contexts) == 3

            assert contexts == ["Context 1", "Context 2", "Context 3"]
            assert metadata["sources"] == ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
            assert metadata["uids"] == ["id1", "id2", "id3"]
            assert metadata["enhanced_rag"] is True

    def test_run_enhanced_rag_pipeline_metadata_processing(self):
        """Test enhanced RAG pipeline metadata processing"""
        query = "Test metadata processing"

        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch("app.services.enhanced_rag_service.generate_answer") as mock_generate,
        ):
            mock_generate.return_value = (
                "Metadata answer",
                [
                    {
                        "text": "Metadata context",
                        "chunk_uid": "id1",
                        "source": "doc1.pdf",
                        "score": 0.85,
                    }
                ],
                {
                    "retrieval": {"retrieval_time": 0.025},
                    "generation": {"generation_time": 0.5},
                    "total_tokens": 150,
                },
            )

            answer, contexts, metadata = run_enhanced_rag_pipeline(query)

            assert answer == "Metadata answer"
            assert contexts == ["Metadata context"]
            assert metadata["enhanced_rag"] is True
            assert metadata["sources"] == ["doc1.pdf"]
            assert metadata["uids"] == ["id1"]
            assert "total_time" in metadata

    def test_run_enhanced_rag_pipeline_does_not_call_mock_on_failure(self):
        """Test enhanced RAG pipeline never invokes the test mock on failure"""
        query = "Test fallback"

        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch(
                "app.services.enhanced_rag_service.generate_answer",
                side_effect=Exception("RAG unavailable"),
            ),
        ):
            with pytest.raises(RAGException):
                run_enhanced_rag_pipeline(query)

        assert not hasattr(enhanced_rag_module, "_mock_enhanced_rag_pipeline")

    def test_run_enhanced_rag_pipeline_stream_mode(self):
        """Test enhanced RAG pipeline in stream mode"""
        query = "Test stream mode"

        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch("app.services.enhanced_rag_service.generate_answer") as mock_generate,
        ):
            mock_generate.return_value = (
                "Stream answer",
                [
                    {
                        "text": "Stream context",
                        "chunk_uid": "id1",
                        "source": "doc1.pdf",
                        "score": 0.9,
                    }
                ],
                {"retrieval": {"retrieval_time": 0.02}},
            )

            answer, contexts, metadata = run_enhanced_rag_pipeline(query)

            assert answer == "Stream answer"
            assert metadata["enhanced_rag"] is True
            mock_generate.assert_called_once()

    def test_run_enhanced_rag_pipeline_integration(self):
        """Test enhanced RAG pipeline integration with all features"""
        query = "Integration test query"
        user_id = "user123"
        channel_id = "channel456"
        request_id = "req789"

        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch("app.services.enhanced_rag_service.generate_answer") as mock_generate,
        ):
            mock_generate.return_value = (
                "Integration answer",
                [
                    {
                        "text": "Context 1",
                        "chunk_uid": "id1",
                        "source": "doc1.pdf",
                        "score": 0.9,
                    },
                    {
                        "text": "Context 2",
                        "chunk_uid": "id2",
                        "source": "doc2.pdf",
                        "score": 0.8,
                    },
                ],
                {
                    "retrieval": {"retrieval_time": 0.03},
                    "generation": {"generation_time": 0.4},
                },
            )

            answer, contexts, metadata = run_enhanced_rag_pipeline(
                query,
                top_k=4,
                user_id=user_id,
                channel_id=channel_id,
                request_id=request_id,
            )

            assert answer == "Integration answer"
            assert contexts == ["Context 1", "Context 2"]
            assert metadata["enhanced_rag"] is True
            assert metadata["sources"] == ["doc1.pdf", "doc2.pdf"]
            assert metadata["uids"] == ["id1", "id2"]
            assert "total_time" in metadata
            mock_generate.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
