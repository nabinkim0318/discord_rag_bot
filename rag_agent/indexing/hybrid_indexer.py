# rag_agent/indexing/hybrid_indexer.py
from __future__ import annotations

import random
from typing import Any, Dict, List

from rag_agent.indexing.embeddings import embed_texts
from rag_agent.indexing.sqlite_fts import (
    fts_count,
    init_sqlite,
    table_count,
    upsert_chunks,
)
from rag_agent.indexing.weaviate_index import ensure_schema, upsert_chunks_with_vectors


def _rows_from_chunks(
    chunks: List[Dict[str, Any]],
    *,
    default_title: str | None = None,
) -> List[Dict[str, Any]]:
    """
    chunk object(dict) → SQLite input record standardization
    기대 입력: {
      'text': ..., 'meta': {doc_id, source, page, section_path, chunk_id, title? ...}
    }
    """
    rows = []
    for ch in chunks:
        meta = ch.get("meta", {})
        doc_id = meta.get("doc_id") or "unknown_doc"
        chunk_id = meta.get("chunk_id")
        if chunk_id is None:
            raise ValueError("meta.chunk_id is required")
        chunk_uid = f"{doc_id}#{int(chunk_id)}"
        rows.append(
            {
                "doc_id": doc_id,
                "chunk_id": int(chunk_id),
                "chunk_uid": chunk_uid,
                "text": ch["text"],
                "title": meta.get("title", default_title),
                "section": meta.get("section_path"),
                "page": meta.get("page"),
                "source": meta.get("source"),
            }
        )
    return rows


def _weaviate_items(
    chunks: List[Dict[str, Any]],
    vectors: List[List[float]],
) -> List[Dict[str, Any]]:
    items = []
    for ch, v in zip(chunks, vectors):
        meta = ch.get("meta", {})
        doc_id = meta.get("doc_id") or "unknown_doc"
        chunk_id = int(meta.get("chunk_id"))
        items.append(
            {
                "chunk_uid": f"{doc_id}#{chunk_id}",
                "content": ch["text"],
                "source": meta.get("source"),
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "page": meta.get("page"),
                "metadata": {
                    "section_path": meta.get("section_path"),
                    "title": meta.get("title"),
                    "ingested_at": meta.get("ingested_at"),
                    "checksum": meta.get("checksum"),
                },
                "vector": v,
            }
        )
    return items


def hybrid_index(
    *,
    sqlite_path: str,
    chunks: List[Dict[str, Any]],
    embed_model: str | None = None,
    weaviate_enabled: bool = True,
) -> Dict[str, Any]:
    """
    1) SQLite+FTS5 (BM25) upsert
    2) embeddings calculation
    3) Weaviate upsert
    4) Synchronization verification (row count match
    & random sample chunk_uid cross-check in separate lookup function)
    """
    # 0) Initialize (only once)
    init_sqlite(sqlite_path)
    if weaviate_enabled:
        ensure_schema()

    # 1) SQLite Indexing
    rows = _rows_from_chunks(chunks)
    n_sql = upsert_chunks(sqlite_path, rows)

    # 2) Embedding
    texts = [ch["text"] for ch in chunks]
    vectors = embed_texts(texts, model=embed_model)

    # 3) Weaviate Indexing
    n_vec = 0
    if weaviate_enabled:
        items = _weaviate_items(chunks, vectors)
        n_vec = upsert_chunks_with_vectors(items)

    return {
        "sqlite_upserts": n_sql,
        "weaviate_upserts": n_vec,
        "sqlite_table_count": table_count(sqlite_path),
        "sqlite_fts_count": fts_count(sqlite_path),
    }


def sample_chunk_uids(chunks: List[Dict[str, Any]], n: int = 5) -> List[str]:
    """Random sample chunk_uid list (for cross-lookup)"""
    meta = [c.get("meta", {}) for c in chunks]
    ids = [
        f"{m.get('doc_id') or 'unknown_doc'}#{int(m['chunk_id'])}"
        for m in meta
        if "chunk_id" in m
    ]
    return random.sample(ids, min(n, len(ids)))
