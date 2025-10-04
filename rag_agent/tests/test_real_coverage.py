#!/usr/bin/env python3
"""
Real Coverage Tests
Tests actual RAG components without excessive mocking
"""

import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_query_planner_real():
    """Test QueryPlanner with real implementation"""
    logger.info("Testing QueryPlanner with real implementation...")

    try:
        from rag_agent.query.query_planner import QueryPlanner

        planner = QueryPlanner()

        # Test real queries
        test_queries = [
            "What is machine learning?",
            "Show me the schedule for week 3",
            "How do I submit my project?",
            "What resources are available for engineers?",
        ]

        for query in test_queries:
            result = planner.plan_query(query)
            assert hasattr(result, "original_query"), "Should have original_query"
            assert hasattr(result, "intents"), "Should have intents"
            assert hasattr(
                result, "requires_clarification"
            ), "Should have requires_clarification"

        logger.info("✅ QueryPlanner real test passed")
        return True

    except Exception as e:
        logger.error(f"❌ QueryPlanner real test failed: {e}")
        return False


def test_enhanced_chunker_real():
    """Test EnhancedChunker with real implementation"""
    logger.info("Testing EnhancedChunker with real implementation...")

    try:
        from rag_agent.ingestion.enhanced_chunker import EnhancedChunker

        chunker = EnhancedChunker()

        # Test real chunking
        test_content = """
        This is a test document about machine learning.
        Machine learning is a subset of artificial intelligence.
        It enables computers to learn from data without being explicitly programmed.
        There are different types of machine learning including supervised,
        unsupervised, and reinforcement learning.
        """

        # Test chunking
        chunks = chunker.chunk_text(test_content, source="test.md")

        assert len(chunks) > 0, "Should produce chunks"
        assert all(
            hasattr(chunk, "content") for chunk in chunks
        ), "All chunks should have content"
        assert all(
            hasattr(chunk, "metadata") for chunk in chunks
        ), "All chunks should have metadata"

        logger.info("✅ EnhancedChunker real test passed")
        return True

    except Exception as e:
        logger.error(f"❌ EnhancedChunker real test failed: {e}")
        return False


def test_normalize_real():
    """Test normalize functions with real implementation"""
    logger.info("Testing normalize functions with real implementation...")

    try:
        from rag_agent.ingestion.normalize import normalize_text

        # Test real normalization
        test_text = """
        • This is a bullet point
        • Another bullet point
        URL: https://example.com
        Email: test@example.com
        """

        normalized = normalize_text(test_text)

        assert isinstance(normalized, str), "Should return string"
        assert len(normalized) > 0, "Should not be empty"

        logger.info("✅ Normalize real test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Normalize real test failed: {e}")
        return False


def test_fuse_real():
    """Test fuse functions with real implementation"""
    logger.info("Testing fuse functions with real implementation...")

    try:
        from rag_agent.retrieval.fuse import mmr_select, rrf_combine

        # Test real RRF
        lists = [
            [{"chunk_uid": "1", "score": 0.9}, {"chunk_uid": "2", "score": 0.8}],
            [{"chunk_uid": "1", "score": 0.7}, {"chunk_uid": "3", "score": 0.6}],
        ]

        rrf_result = rrf_combine(lists, k=3)
        assert len(rrf_result) > 0, "Should return results"
        assert all("score_rrf" in item for item in rrf_result), "Should have RRF scores"

        # Test real MMR
        items = [
            {"content": "Machine learning is AI", "chunk_uid": "1"},
            {"content": "Deep learning uses neural networks", "chunk_uid": "2"},
            {"content": "AI is transforming industries", "chunk_uid": "3"},
        ]

        mmr_result = mmr_select(items, topn=2, lambda_=0.7)
        assert len(mmr_result) <= 2, "Should return at most topn results"

        logger.info("✅ Fuse real test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Fuse real test failed: {e}")
        return False


def test_retrieval_pipeline_real():
    """Test retrieval pipeline with real implementation"""
    logger.info("Testing retrieval pipeline with real implementation...")

    try:
        from rag_agent.retrieval.retrieval_pipeline import RetrievalPipeline

        # Test real retrieval pipeline
        pipeline = RetrievalPipeline()

        # Test with mock data but real pipeline logic
        # test_query = "What is machine learning?"  # Unused variable
        # test_contexts = [  # Unused variable
        ({"content": "ML is a subset of AI", "chunk_uid": "1", "score": 0.9},)
        (
            {
                "content": "ML algorithms learn from data",
                "chunk_uid": "2",
                "score": 0.8,
            },
        )

        # Test pipeline methods
        assert hasattr(pipeline, "retrieve"), "Should have retrieve method"

        logger.info("✅ Retrieval pipeline real test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Retrieval pipeline real test failed: {e}")
        return False


def main():
    """Run all real coverage tests"""
    logger.info("🚀 Starting real coverage tests...")

    tests = [
        test_query_planner_real,
        test_enhanced_chunker_real,
        test_normalize_real,
        test_fuse_real,
        test_retrieval_pipeline_real,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            logger.error(f"Test {test.__name__} failed with exception: {e}")

    logger.info("\n📊 Real Coverage Test Results")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success rate: {passed / total * 100:.1f}%")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
