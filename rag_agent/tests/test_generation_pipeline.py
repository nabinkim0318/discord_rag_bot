# rag_agent/tests/test_generation_pipeline.py
from unittest.mock import patch

from rag_agent.generation.generation_pipeline import generate_answer


def test_generate_answer_smoke():
    """Test generate_answer with mocked LLM to avoid credential requirements."""

    # Mock hybrid_retrieve to return mock contexts
    with patch(
        "rag_agent.generation.generation_pipeline.hybrid_retrieve"
    ) as mock_retrieve:
        mock_retrieve.return_value = [
            {
                "chunk_uid": "test-chunk-1",
                "text": "Office hours are 9 AM to 5 PM",
                "score": 0.95,
                "source": "test_doc.pdf",
            }
        ]

        # Mock the llm_generate function directly in the generation_pipeline module
        with patch("rag_agent.generation.generation_pipeline.llm_generate") as mock_llm:
            mock_llm.return_value = "Mock answer for office hours: 9 AM - 5 PM"

            out, chosen, meta = generate_answer(
                "What are office hours?", k_final=3, reranker=None, stream=False
            )

            assert isinstance(out, str)
            assert isinstance(chosen, list)
            assert "packing" in meta
            assert len(chosen) > 0  # Should have mock contexts
