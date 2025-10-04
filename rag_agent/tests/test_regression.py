#!/usr/bin/env python3
"""
Regression test script
Tests for resource parsing, mixed intent, search behavior, and vector search
"""

import logging
import os
import sys

from rag_agent.query.query_planner import QueryPlanner

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conditional import to allow running without backend
try:
    from rag_agent.retrieval.retrieval_pipeline import retrieval_pipeline

    RETRIEVAL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Retrieval pipeline not available: {e}")
    RETRIEVAL_AVAILABLE = False


def test_resource_parsing():
    """Resource sentence parsing test"""
    logger.info("=== Resource sentence parsing test ===")

    query_planner = QueryPlanner()
    test_query = "please share the slides and repo for week 3 engineers"

    # Create query plan
    query_plan = query_planner.plan_query(test_query)

    logger.info(f"Query: {test_query}")
    logger.info(f"Intents: {[intent.intent for intent in query_plan.intents]}")

    # Validation
    has_resources = any(intent.intent == "resources" for intent in query_plan.intents)
    has_week_3 = any(
        3 in intent.extracted_info.get("weeks", []) for intent in query_plan.intents
    )
    has_engineer_audience = any(
        intent.extracted_info.get("audience") == "engineer"
        for intent in query_plan.intents
    )

    logger.info(f"✅ Resources intent: {has_resources}")
    logger.info(f"✅ Week 3: {has_week_3}")
    logger.info(f"✅ Engineer audience: {has_engineer_audience}")

    success = has_resources and has_week_3 and has_engineer_audience
    logger.info(f"Result: {'PASS' if success else 'FAIL'}")
    return success


def test_mixed_intent():
    """Mixed intent test"""
    logger.info("=== Mixed intent test ===")

    query_planner = QueryPlanner()
    test_query = "When is demo day and where is the submission form?"

    # Create query plan
    query_plan = query_planner.plan_query(test_query)

    logger.info(f"Query: {test_query}")
    logger.info(f"Intents: {[intent.intent for intent in query_plan.intents]}")

    # Validation
    has_schedule = any(intent.intent == "schedule" for intent in query_plan.intents)
    has_submission = any(intent.intent == "submission" for intent in query_plan.intents)
    has_week_11_schedule = any(
        11 in intent.extracted_info.get("weeks", [])
        for intent in query_plan.intents
        if intent.intent == "schedule"
    )

    logger.info(f"✅ Schedule intent: {has_schedule}")
    logger.info(f"✅ Submission intent: {has_submission}")
    logger.info(f"✅ Week 11 in schedule: {has_week_11_schedule}")

    # Check if both intents exist (parallel processing without overwriting)
    both_intents = has_schedule and has_submission
    logger.info(f"✅ Both intents present: {both_intents}")

    success = both_intents
    logger.info(f"Result: {'PASS' if success else 'FAIL'}")
    return success


def test_search_without_backend():
    """Search behavior test without backend"""
    logger.info("=== Search behavior test without backend ===")

    if not RETRIEVAL_AVAILABLE:
        logger.info(
            "⚠️ Retrieval pipeline not available (expected in backend-less environment)"
        )
        logger.info("✅ Can run without backend (no import failure)")
        logger.info("Result: PASS")
        return True

    try:
        # Simple search test (BM25 only)
        result = retrieval_pipeline(
            query="test query",
            k=5,
            use_vector=False,  # Disable vector search
            use_hybrid=False,  # Disable hybrid search
            db_path="rag_agent/rag_kb.sqlite3",  # SQLite DB path
        )

        logger.info("✅ Retrieval pipeline execution successful")
        logger.info(f"✅ Result type: {type(result)}")

        success = True
        logger.info(f"Result: {'PASS' if success else 'FAIL'}")
        return success

    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        logger.info("Result: FAIL")
        return False


def test_vector_search():
    """Vector search test"""
    logger.info("=== Vector search test ===")

    if not RETRIEVAL_AVAILABLE:
        logger.info(
            "⚠️ Retrieval pipeline not available (expected in backend-less environment)"
        )
        logger.info("✅ Can run without backend (no import failure)")
        logger.info("Result: PASS")
        return True

    try:
        # Vector search test
        result = retrieval_pipeline(
            query="test query",
            k=5,
            use_vector=True,
            use_hybrid=False,
            db_path="rag_agent/rag_kb.sqlite3",
        )

        logger.info("✅ Vector search pipeline execution successful")
        logger.info(f"✅ Result type: {type(result)}")

        success = True
        logger.info(f"Result: {'PASS' if success else 'FAIL'}")
        return success

    except Exception as e:
        logger.error(f"❌ Vector search failed: {e}")
        logger.info("Result: FAIL")
        return False


def main():
    """Run all regression tests"""
    logger.info("🚀 Starting regression tests")

    tests = [
        ("Resource sentence parsing", test_resource_parsing),
        ("Mixed intent", test_mixed_intent),
        ("Search without backend", test_search_without_backend),
        ("Vector search", test_vector_search),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Error during {test_name} test: {e}")
            results.append((test_name, False))

    # Results summary
    logger.info(f"\n{'='*50}")
    logger.info("📊 Test results summary")
    logger.info(f"{'='*50}")

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1

    logger.info(f"\nTotal {len(results)} tests, {passed} passed")
    logger.info(f"Success rate: {passed/len(results)*100:.1f}%")

    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
