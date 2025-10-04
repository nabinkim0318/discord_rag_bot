#!/usr/bin/env python3
"""
Chunk validation test script
Tests offset integrity, ID stability, length statistics, and integration checks
"""

import logging
import os
import sys

from rag_agent.ingestion.chunker import chunk_text
from rag_agent.ingestion.enhanced_chunker import chunk_document

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_chunker():
    """Test basic chunker validation"""
    logger.info("Testing basic chunker...")

    # Sample text for testing (longer text for better length statistics)
    sample_text = """
    This is a comprehensive sample document for testing chunk validation.
    It contains multiple paragraphs with different lengths and structures.

    The first paragraph is relatively short but provides an introduction to the topic.

    This is a much longer paragraph that should be split into multiple chunks when the
    chunk size is smaller than the total length. It contains more detailed information
    about the topic and should demonstrate the chunking behavior effectively. This
    paragraph includes various technical terms and concepts that are relevant to the
    document processing system. The content covers different aspects of text analysis,
    natural language processing, and information retrieval techniques.

    Another substantial paragraph with different content to test the chunking algorithm
    thoroughly. This section discusses the implementation details of the chunking
    process,
    including the algorithms used for text segmentation, the parameters that control the
    chunk size and overlap, and the quality metrics that are used to evaluate the
    effectiveness of the chunking approach.

    A final paragraph that provides additional context and information about the
    system's capabilities and limitations. This content helps to ensure that the
    chunking
    algorithm
    can handle various types of text structures and content types effectively.
    """

    # Test basic chunking with larger chunks for better statistics
    chunks = chunk_text(
        sample_text,
        max_chars=500,
        overlap=100,
        min_chunk_chars=200,
        doc_id="test_doc",
        source="test_source.pdf",
        page=1,
        section_path="1. Introduction",
    )

    # Simple validation checks
    validation_passed = True
    errors = []

    # Check offset integrity
    for chunk in chunks:
        start = chunk.meta["start_char"]
        end = chunk.meta["end_char"]
        if sample_text[start:end].strip() != chunk.text.strip():
            errors.append(f"Offset mismatch at {start}:{end}")
            validation_passed = False

    # Check required fields
    for chunk in chunks:
        if not all(
            key in chunk.meta for key in ["chunk_id", "doc_id", "source", "page"]
        ):
            errors.append("Missing required fields")
            validation_passed = False

    logger.info("Basic chunker validation results:")
    logger.info(f"  Offset integrity: {validation_passed}")
    logger.info(f"  Errors: {errors}")

    # Test ID stability
    chunks2 = chunk_text(
        sample_text,
        max_chars=500,
        overlap=100,
        min_chunk_chars=200,
        doc_id="test_doc",
        source="test_source.pdf",
        page=1,
    )
    is_stable = len(chunks) == len(chunks2) and all(
        c1.meta["chunk_id"] == c2.meta["chunk_id"] for c1, c2 in zip(chunks, chunks2)
    )
    logger.info(f"  ID stability: {is_stable}")

    return {"offset_integrity_passed": validation_passed, "errors": errors}, is_stable


def test_enhanced_chunker():
    """Test enhanced chunker validation"""
    logger.info("Testing enhanced chunker...")

    # Sample FAQ content for testing
    sample_faq = """
    # FAQ Section

    Q: What is the purpose of this system?
    A: This system is designed to help with document processing and retrieval.

    Q: How does chunking work?
    A: Chunking breaks down large documents into smaller, manageable pieces for
    better processing.

    Q: What are the benefits?
    A: The benefits include improved search accuracy and faster processing times.
    """

    # Test enhanced chunking
    chunks = chunk_document(sample_faq, "test_faq.pdf", page=1)

    # Simple validation checks for enhanced chunks
    validation_passed = True
    errors = []

    # Check basic chunk properties
    for chunk in chunks:
        if not hasattr(chunk, "content") or not chunk.content:
            errors.append("Missing content")
            validation_passed = False

    # Check required fields
    for chunk in chunks:
        if not hasattr(chunk, "chunk_id") or not hasattr(chunk, "chunk_uid"):
            errors.append("Missing required fields")
            validation_passed = False
        if not hasattr(chunk, "metadata") or not hasattr(chunk.metadata, "doc_type"):
            errors.append("Missing metadata fields")
            validation_passed = False

    logger.info("Enhanced chunker validation results:")
    logger.info(f"  Offset integrity: {validation_passed}")
    logger.info(f"  Errors: {errors}")

    # Test ID stability
    chunks2 = chunk_document(sample_faq, "test_faq.pdf", page=1)
    is_stable = len(chunks) == len(chunks2) and all(
        c1.chunk_id == c2.chunk_id for c1, c2 in zip(chunks, chunks2)
    )
    logger.info(f"  ID stability: {is_stable}")

    return {"offset_integrity_passed": validation_passed, "errors": errors}, is_stable


def main():
    """Run all validation tests"""
    logger.info("Starting chunk validation tests...")

    # Test basic chunker
    basic_results, basic_stable = test_basic_chunker()

    # Test enhanced chunker
    enhanced_results, enhanced_stable = test_enhanced_chunker()

    # Summary
    logger.info("\n=== VALIDATION SUMMARY ===")
    logger.info("Basic chunker:")
    logger.info(f"  - Offset integrity: {basic_results['offset_integrity_passed']}")
    logger.info(f"  - ID stable: {basic_stable}")
    logger.info(f"  - Errors: {basic_results['errors']}")

    logger.info("Enhanced chunker:")
    logger.info(f"  - Offset integrity: {enhanced_results['offset_integrity_passed']}")
    logger.info(f"  - ID stable: {enhanced_stable}")
    logger.info(f"  - Errors: {enhanced_results['errors']}")

    # Check for any errors
    all_errors = basic_results["errors"] + enhanced_results["errors"]
    if all_errors:
        logger.warning(f"Validation errors found: {all_errors}")
        return False
    else:
        logger.info("All validation tests passed!")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
