# rag_agent/indexing/weaviate_index.py
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Iterable, List

try:
    import weaviate
except Exception:
    weaviate = None

from app.core.config import settings  # Assume backend settings reuse

CLASS_NAME = "KBChunk"  # Recommended class name (separate from RAGDocument)
NAMESPACE = uuid.UUID(
    "00000000-0000-0000-0000-00000000KBCH"
)  # fixed namespace (16진수 32자)


def _client():
    if weaviate is None:
        raise RuntimeError("weaviate is not installed")
    # v3 client based (v4 connect requires separate branch)
    cfg = {"url": settings.WEAVIATE_URL}
    if getattr(settings, "WEAVIATE_API_KEY", None):
        cfg["auth_client_secret"] = weaviate.AuthApiKey(
            api_key=settings.WEAVIATE_API_KEY
        )
    return weaviate.Client(**cfg)


def _class_exists(c: "weaviate.Client", class_name: str) -> bool:
    # v3: schema.get() 후 classes 내에 존재 여부 검사
    sch = c.schema.get()
    classes = (sch or {}).get("classes", []) or []
    return any(cl.get("class") == class_name for cl in classes)


def ensure_schema():
    c = _client()
    try:
        if _class_exists(c, CLASS_NAME):
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


def uuid_from_chunk_uid(chunk_uid: str) -> str:
    """
    chunk_uid(예: 'DOC123#45') → fixed uuid5
    - same chunk_uid always generates the same UUID → idempotent upsert guarantee
    """
    # uuid5 is stable UUID generation from string input
    return str(uuid.uuid5(NAMESPACE, chunk_uid))


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
    - uuid derived from chunk_uid(uuid5) → idempotent
    """
    cnt = 0
    c = _client()
    try:
        with c.batch as batch:
            batch.configure(batch_size=batch_size, timeout_retries=3)
            for it in items:
                cu = it["chunk_uid"]
                uid = uuid_from_chunk_uid(cu)
                props = {
                    "content": it["content"],
                    "source": it.get("source"),
                    "doc_id": it.get("doc_id"),
                    "chunk_id": int(it.get("chunk_id", 0)),
                    "page": it.get("page"),
                    "chunk_uid": cu,
                    "metadata_json": json.dumps(
                        it.get("metadata", {}), ensure_ascii=False
                    ),
                }
                # v3 client: same uuid add → merge-append instead of fail if existing
                # for safety, try/except fallback to update
                try:
                    c.batch.add_data_object(
                        data_object=props,
                        class_name=CLASS_NAME,
                        vector=it[vector_key],
                        uuid=uid,
                    )
                    cnt += 1
                except Exception:
                    # if already exists, use separate update API
                    c.data_object.update(
                        data_object=props,
                        class_name=CLASS_NAME,
                        uuid=uid,
                    )
                    # vector also needs update(weaviate v3
                    # does not support separate vector update →
                    # fallback to re-upsert)
                    # some distributions do not provide .objects.update_vector.
                    # consider re-upsert strategy if needed.
                    cnt += 1
    finally:
        c.close()
    return cnt


def get_count() -> int:
    """total object count (approximate) → Aggregate count"""
    c = _client()
    try:
        q = c.query.aggregate(CLASS_NAME).with_fields("meta { count }")
        res = q.do()
        return int(res["data"]["Aggregate"][CLASS_NAME][0]["meta"]["count"])
    finally:
        c.close()


def fetch_by_chunk_uid(chunk_uids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    fetch objects by chunk_uid list → {chunk_uid: props}
    - for large amounts, multiple GraphQL where+limit calls are needed.
    this is for small sample.
    """
    out: Dict[str, Dict[str, Any]] = {}
    if not chunk_uids:
        return out
    c = _client()
    try:
        for cu in chunk_uids:
            uid = uuid_from_chunk_uid(cu)
            obj = c.data_object.get_by_id(uid, class_name=CLASS_NAME)
            if obj:
                props = obj.get("properties") or {}
                out[cu] = props
    finally:
        c.close()
    return out
