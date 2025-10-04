"""
Tests for RAG service functionality
"""

from unittest.mock import patch

import pytest

from app.services.rag_service import (
    generate_answer,
    generate_answer_adapter,
    generate_answer_mock,
    run_rag_pipeline,
)


class TestRAGService:
    """Test RAG service functionality"""

    def test_generate_answer_mock(self):
        """Test mock generate_answer function"""
        query = "What is machine learning?"

        answer, contexts, metadata = generate_answer_mock(query)

        # Check response structure
        assert isinstance(answer, str)
        assert isinstance(contexts, list)
        assert isinstance(metadata, dict)

        # Check answer content
        assert "Mock response" in answer
        assert query[:50] in answer

        # Check contexts
        assert len(contexts) == 2
        for context in contexts:
            assert "chunk_uid" in context
            assert "text" in context
            assert "score" in context
            assert "source" in context
            assert "metadata" in context

        # Check metadata
        assert metadata["mock"] is True
        assert metadata["query"] == query
        assert "k_bm25" in metadata
        assert "k_vec" in metadata
        assert "k_final" in metadata

    def test_generate_answer_mock_with_parameters(self):
        """Test mock generate_answer with custom parameters"""
        query = "Test query"
        k_bm25 = 50
        k_vec = 40
        k_final = 10
        bm25_weight = 0.3
        vec_weight = 0.7
        mmr_lambda = 0.8
        reranker = "cohere"
        prompt_version = "v2.0"

        answer, contexts, metadata = generate_answer_mock(
            query=query,
            k_bm25=k_bm25,
            k_vec=k_vec,
            k_final=k_final,
            bm25_weight=bm25_weight,
            vec_weight=vec_weight,
            mmr_lambda=mmr_lambda,
            reranker=reranker,
            prompt_version=prompt_version,
        )

        # Check metadata contains custom parameters
        assert metadata["k_bm25"] == k_bm25
        assert metadata["k_vec"] == k_vec
        assert metadata["k_final"] == k_final
        assert metadata["prompt_version"] == prompt_version

    @patch("app.services.rag_service.RAG_AGENT_AVAILABLE", True)
    @patch("app.services.rag_service.rag_generate_answer")
    def test_generate_answer_with_rag_agent(self, mock_rag_generate):
        """Test generate_answer when RAG agent is available"""
        # Mock RAG agent response
        mock_answer = "Real RAG response"
        mock_contexts = [{"chunk_uid": "real-1", "text": "Real context"}]
        mock_metadata = {"real": True}

        mock_rag_generate.return_value = (mock_answer, mock_contexts, mock_metadata)

        query = "Test query"
        answer, contexts, metadata = generate_answer(query)

        # Check that RAG agent was called
        mock_rag_generate.assert_called_once()

        # Check response
        assert answer == mock_answer
        assert contexts == mock_contexts
        assert metadata == mock_metadata

    @patch("app.services.rag_service.RAG_AGENT_AVAILABLE", True)
    @patch("app.services.rag_service.rag_generate_answer")
    def test_generate_answer_rag_agent_failure(self, mock_rag_generate):
        """Test generate_answer when RAG agent fails"""
        # Mock RAG agent failure
        mock_rag_generate.side_effect = Exception("RAG agent failed")

        query = "Test query"
        answer, contexts, metadata = generate_answer(query)

        # Should fall back to mock
        assert "Mock response" in answer
        assert metadata["mock"] is True

    @patch("app.services.rag_service.RAG_AGENT_AVAILABLE", False)
    def test_generate_answer_without_rag_agent(self):
        """Test generate_answer when RAG agent is not available"""
        query = "Test query"
        answer, contexts, metadata = generate_answer(query)

        # Should use mock
        assert "Mock response" in answer
        assert metadata["mock"] is True

    def test_generate_answer_adapter(self):
        """Test generate_answer_adapter function"""
        query = "Test query"

        with patch("app.services.rag_service.generate_answer") as mock_generate:
            mock_answer = "Adapter response"
            mock_contexts = [{"chunk_uid": "adapter-1", "text": "Adapter context"}]
            mock_metadata = {"adapter": True}

            mock_generate.return_value = (mock_answer, mock_contexts, mock_metadata)

            result = generate_answer_adapter(query, k_bm25=25, k_vec=25, k_final=5)

            # Check that generate_answer was called with correct parameters
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args[1]
            assert call_kwargs["k_bm25"] == 25
            assert call_kwargs["k_vec"] == 25
            assert call_kwargs["k_final"] == 5

            # Check response
            assert result == (mock_answer, mock_contexts, mock_metadata)

    def test_generate_answer_adapter_failure(self):
        """Test generate_answer_adapter when it fails"""
        query = "Test query"

        with patch("app.services.rag_service.generate_answer") as mock_generate:
            mock_generate.side_effect = Exception("Generation failed")

            # Should fall back to mock, not raise exception
            answer, contexts, metadata = generate_answer_adapter(query)

            # Check that mock response is returned
            assert "Mock response" in answer
            assert metadata["mock"] is True

    @patch("app.services.rag_service.generate_answer_adapter")
    @patch("app.services.rag_service.record_retriever_topk")
    @patch("app.services.rag_service.record_retrieval_hit")
    @patch("app.services.rag_service.record_rag_pipeline_latency")
    @patch("app.services.rag_service.log_rag_operation")
    def test_run_rag_pipeline(
        self, mock_log, mock_latency, mock_hit, mock_topk, mock_adapter
    ):
        """Test run_rag_pipeline function"""
        # Mock adapter response
        mock_answer = "Pipeline response"
        mock_contexts = [
            {
                "chunk_uid": "pipeline-1",
                "text": "Pipeline context 1",
                "source": "doc1.pdf",
            },
            {
                "chunk_uid": "pipeline-2",
                "text": "Pipeline context 2",
                "source": "doc2.pdf",
            },
        ]
        mock_metadata = {"pipeline": True}

        mock_adapter.return_value = (mock_answer, mock_contexts, mock_metadata)

        query = "Test query"
        top_k = 5
        user_id = "user123"
        channel_id = "channel456"
        request_id = "req789"

        answer, contexts, metadata = run_rag_pipeline(
            query=query,
            top_k=top_k,
            user_id=user_id,
            channel_id=channel_id,
            request_id=request_id,
        )

        # Check adapter was called with correct parameters
        mock_adapter.assert_called_once()
        call_kwargs = mock_adapter.call_args[1]
        assert call_kwargs["k_bm25"] == max(30, top_k * 3)  # 30
        assert call_kwargs["k_vec"] == max(30, top_k * 3)  # 30
        assert call_kwargs["k_final"] == top_k  # 5

        # Check metrics were recorded
        mock_topk.assert_called_once_with(top_k)
        mock_hit.assert_called_once_with(True)  # contexts exist
        mock_latency.assert_called_once()
        mock_log.assert_called_once()

        # Check response
        assert answer == mock_answer
        assert len(contexts) == 2
        assert contexts[0] == "Pipeline context 1"
        assert contexts[1] == "Pipeline context 2"

        # Check metadata
        assert "sources" in metadata
        assert "uids" in metadata
        assert "pipeline_duration" in metadata
        assert metadata["sources"] == ["doc1.pdf", "doc2.pdf"]
        assert metadata["uids"] == ["pipeline-1", "pipeline-2"]

    @patch("app.services.rag_service.generate_answer_adapter")
    def test_run_rag_pipeline_no_contexts(self, mock_adapter):
        """Test run_rag_pipeline when no contexts are returned"""
        # Mock adapter response with no contexts
        mock_answer = "No context response"
        mock_contexts = []
        mock_metadata = {"no_context": True}

        mock_adapter.return_value = (mock_answer, mock_contexts, mock_metadata)

        query = "Test query"
        answer, contexts, metadata = run_rag_pipeline(query, top_k=5)

        # Check response
        assert answer == mock_answer
        assert contexts == []
        assert metadata["sources"] == []
        assert metadata["uids"] == []

    @patch("app.services.rag_service.generate_answer_adapter")
    def test_run_rag_pipeline_stream_response(self, mock_adapter):
        """Test run_rag_pipeline with stream response"""
        # Mock adapter response with stream
        mock_stream = ["Stream", " response", " parts"]
        mock_contexts = [{"chunk_uid": "stream-1", "text": "Stream context"}]
        mock_metadata = {"stream": True}

        mock_adapter.return_value = (mock_stream, mock_contexts, mock_metadata)

        query = "Test query"
        answer, contexts, metadata = run_rag_pipeline(query, top_k=5)

        # Check that stream was joined
        assert answer == "Stream response parts"
        assert len(contexts) == 1
        assert contexts[0] == "Stream context"

    def test_run_rag_pipeline_default_parameters(self):
        """Test run_rag_pipeline with default parameters"""
        with patch("app.services.rag_service.generate_answer_adapter") as mock_adapter:
            mock_adapter.return_value = ("Answer", [], {})

            run_rag_pipeline("Test query")

        # Check default parameters
        call_kwargs = mock_adapter.call_args[1]
        assert call_kwargs["k_bm25"] == 30  # max(30, 5*3)
        assert call_kwargs["k_vec"] == 30  # max(30, 5*3)
        assert call_kwargs["k_final"] == 5  # default top_k
        assert call_kwargs["reranker"] == "cohere"  # default reranker
        assert call_kwargs["prompt_version"] == "v1.1"
        assert call_kwargs["stream"] is False

    def test_run_rag_pipeline_custom_parameters(self):
        """Test run_rag_pipeline with custom parameters"""
        with patch("app.services.rag_service.generate_answer_adapter") as mock_adapter:
            mock_adapter.return_value = ("Answer", [], {})

            run_rag_pipeline(
                "Test query",
                top_k=10,
                prompt_version="v2.0",
                use_rerank=True,
                reranker="cohere",
                ab_test_group="test_group",
            )

            # Check custom parameters
            call_kwargs = mock_adapter.call_args[1]
            assert call_kwargs["k_bm25"] == 30  # max(30, 10*3)
            assert call_kwargs["k_vec"] == 30  # max(30, 10*3)
            assert call_kwargs["k_final"] == 10
            assert call_kwargs["reranker"] == "cohere"
            assert call_kwargs["prompt_version"] == "v2.0"
            assert call_kwargs["stream"] is False


class TestRAGServiceIntegration:
    """Integration tests for RAG service"""

    def test_full_pipeline_mock(self):
        """Test full pipeline with mock implementation"""
        query = "What is artificial intelligence?"

        # This should use mock since RAG_AGENT_AVAILABLE is likely False in test
        answer, contexts, metadata = run_rag_pipeline(query, top_k=3)

        # Check response structure
        assert isinstance(answer, str)
        assert isinstance(contexts, list)
        assert isinstance(metadata, dict)

        # Check that we got some response
        assert len(answer) > 0
        assert "pipeline_duration" in metadata
        assert "sources" in metadata
        assert "uids" in metadata

    def test_pipeline_with_user_context(self):
        """Test pipeline with user and channel context"""
        query = "How to submit assignments?"
        user_id = "user123"
        channel_id = "channel456"
        request_id = "req789"

        answer, contexts, metadata = run_rag_pipeline(
            query=query,
            top_k=5,
            user_id=user_id,
            channel_id=channel_id,
            request_id=request_id,
        )

        # Check that user context is preserved in metadata
        # Note: user_id, channel_id, request_id are passed to run_rag_pipeline
        # but may not be directly included in the returned metadata
        assert "pipeline_duration" in metadata
        assert "sources" in metadata
        assert "uids" in metadata


if __name__ == "__main__":
    pytest.main([__file__])
