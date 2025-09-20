# rag_agent/indexing/weaviate_index.py
from __future__ import annotations

import json
from typing import Any, Dict, Iterable

try:
    import weaviate
except Exception:
    weaviate = None

from app.core.config import settings  # Assume backend settings reuse

CLASS_NAME = "KBChunk"  # Recommended class name (separate from RAGDocument)


def _client():
    if weaviate is None:
        raise RuntimeError("weaviate is not installed")
    # v3 client based (v4 connect requires separate branch)
    cfg = {"url": settings.WEAVIATE_URL}
    if settings.WEAVIATE_API_KEY:
        cfg["auth_client_secret"] = weaviate.AuthApiKey(
            api_key=settings.WEAVIATE_API_KEY
        )
    return weaviate.Client(**cfg)


def ensure_schema():
    c = _client()
    try:
        if c.schema.exists(CLASS_NAME):
            return
        class_schema = {
            "class": CLASS_NAME,
            "description": "KB chunks for hybrid RAG",
            "vectorizer": "none",  # External embedding injection
            "properties": [
                {"name": "content", "dataType": ["text"]},
                {"name": "source", "dataType": ["string"]},
                {"name": "doc_id", "dataType": ["string"]},
                {"name": "chunk_id", "dataType": ["int"]},
                {"name": "page", "dataType": ["int"]},
                {"name": "chunk_uid", "dataType": ["string"]},
                {"name": "metadata_json", "dataType": ["text"]},
            ],
        }
        c.schema.create_class(class_schema)
    finally:
        c.close()


def upsert_chunks_with_vectors(
    items: Iterable[Dict[str, Any]],
    *,
    vector_key: str = "vector",
    batch_size: int = 100,
) -> int:
    """
    items: [{
      'chunk_uid', 'content', 'source', 'doc_id', 'chunk_id',
      'page', 'metadata' (dict), 'vector' (list[float])
    }, ...]
    """
    cnt = 0
    c = _client()
    try:
        with c.batch as batch:
            batch.configure(batch_size=batch_size, timeout_retries=3)
            for it in items:
                props = {
                    "content": it["content"],
                    "source": it.get("source"),
                    "doc_id": it.get("doc_id"),
                    "chunk_id": int(it.get("chunk_id", 0)),
                    "page": it.get("page"),
                    "chunk_uid": it["chunk_uid"],
                    "metadata_json": json.dumps(
                        it.get("metadata", {}), ensure_ascii=False
                    ),
                }
                c.batch.add_data_object(
                    data_object=props,
                    class_name=CLASS_NAME,
                    vector=it[vector_key],
                    uuid=None,  # chunk_uid as separate property, uuid is auto
                )
                cnt += 1
    finally:
        c.close()
    return cnt
