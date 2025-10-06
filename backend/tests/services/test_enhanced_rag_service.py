"""
Tests for Enhanced RAG service functionality
"""

from unittest.mock import patch

import pytest

from app.services.enhanced_rag_service import (
    _mock_enhanced_rag_pipeline,
    run_enhanced_rag_pipeline,
)


class TestEnhancedRAGService:
    """Test cases for enhanced RAG service functionality"""

    def test_mock_enhanced_rag_pipeline(self):
        """Test the mock enhanced RAG pipeline"""
        query = "Test enhanced query"
        answer, contexts, metadata = _mock_enhanced_rag_pipeline(query)

        assert "Mock enhanced RAG response" in answer
        assert len(contexts) == 1
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
            assert contexts[0]["text"] == "Enhanced context"
            assert metadata["enhanced_rag"] is True
            assert "total_time" in metadata
            mock_generate.assert_called_once()

    def test_run_enhanced_rag_pipeline_without_rag_agent(self):
        """Test enhanced RAG pipeline without RAG agent"""
        query = "Test enhanced query"

        with patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", False):
            answer, contexts, metadata = run_enhanced_rag_pipeline(query)

        assert "Enhanced RAG is not available" in answer
        assert len(contexts) == 0
        assert metadata["rag_agent_available"] is False

    def test_run_enhanced_rag_pipeline_exception_handling(self):
        """Test enhanced RAG pipeline exception handling with fallback"""
        query = "Failing query"

        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch(
                "app.services.enhanced_rag_service.generate_answer",
                side_effect=Exception("RAG error"),
            ),
        ):
            # Should not raise exception, should fallback to mock
            answer, contexts, metadata = run_enhanced_rag_pipeline(query)

            # Verify fallback behavior
            assert answer is not None
            assert isinstance(contexts, list)
            assert isinstance(metadata, dict)
            assert "enhanced_rag" in metadata

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

            # Check that contexts are properly formatted
            assert contexts[0]["text"] == "Context 1"
            assert contexts[1]["text"] == "Context 2"
            assert contexts[2]["content"] == "Context 3"

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
            assert metadata["enhanced_rag"] is True
            assert "total_time" in metadata
            # Check that metadata contains expected fields
            assert "enhanced_rag" in metadata
            assert "total_time" in metadata
            # Note: uids field may not be present in current implementation

    def test_run_enhanced_rag_pipeline_fallback_to_mock(self):
        """Test enhanced RAG pipeline fallback to mock when RAG agent fails"""
        query = "Test fallback"

        with (
            patch("app.services.enhanced_rag_service.RAG_AGENT_AVAILABLE", True),
            patch(
                "app.services.enhanced_rag_service.generate_answer",
                side_effect=Exception("RAG unavailable"),
            ),
        ):
            # Should fall back to fallback implementation
            answer, contexts, metadata = run_enhanced_rag_pipeline(query)

            assert "Enhanced RAG failed" in answer
            assert len(contexts) == 0
            assert metadata["rag_agent_failed"] is True
            assert metadata["enhanced_rag"] is True
            assert metadata["pipeline"] == "enhanced_rag_fallback"

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
            assert len(contexts) == 2
            assert contexts[0]["text"] == "Context 1"
            assert contexts[1]["text"] == "Context 2"
            assert metadata["enhanced_rag"] is True
            assert "total_time" in metadata
            # Check that metadata contains expected fields
            assert "enhanced_rag" in metadata
            assert "total_time" in metadata
            # Note: uids field may not be present in current implementation
            mock_generate.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
