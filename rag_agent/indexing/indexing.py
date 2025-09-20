# rag_agent/indexing/indexing.py
from __future__ import annotations

import logging
from typing import Any, Dict, List

log = logging.getLogger(__name__)


def validate_chunk_data(chunk: Dict[str, Any]) -> bool:
    """
    Validate that a chunk has the required fields for indexing.

    Args:
        chunk: Dictionary containing chunk data

    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ["text", "meta"]
    if not all(field in chunk for field in required_fields):
        return False

    meta = chunk.get("meta", {})
    required_meta_fields = ["doc_id", "chunk_id"]
    if not all(field in meta for field in required_meta_fields):
        return False

    return True


def prepare_chunks_for_indexing(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prepare and validate chunks for indexing.

    Args:
        chunks: List of chunk dictionaries

    Returns:
        List of validated chunks ready for indexing
    """
    valid_chunks = []
    for i, chunk in enumerate(chunks):
        if validate_chunk_data(chunk):
            valid_chunks.append(chunk)
        else:
            log.warning(f"Skipping invalid chunk at index {i}: missing required fields")

    return valid_chunks


def get_chunk_uid(doc_id: str, chunk_id: int) -> str:
    """
    Generate a unique identifier for a chunk.

    Args:
        doc_id: Document identifier
        chunk_id: Chunk identifier within the document

    Returns:
        Unique chunk identifier
    """
    return f"{doc_id}#{chunk_id}"


def extract_text_from_chunks(chunks: List[Dict[str, Any]]) -> List[str]:
    """
    Extract text content from a list of chunks.

    Args:
        chunks: List of chunk dictionaries

    Returns:
        List of text strings
    """
    return [chunk.get("text", "") for chunk in chunks]


def get_indexing_stats(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get statistics about the chunks to be indexed.

    Args:
        chunks: List of chunk dictionaries

    Returns:
        Dictionary containing indexing statistics
    """
    if not chunks:
        return {
            "total_chunks": 0,
            "total_text_length": 0,
            "avg_text_length": 0,
            "doc_ids": set(),
        }

    total_length = sum(len(chunk.get("text", "")) for chunk in chunks)
    doc_ids = set(chunk.get("meta", {}).get("doc_id") for chunk in chunks)

    return {
        "total_chunks": len(chunks),
        "total_text_length": total_length,
        "avg_text_length": total_length / len(chunks) if chunks else 0,
        "doc_ids": doc_ids,
        "unique_docs": len(doc_ids),
    }
