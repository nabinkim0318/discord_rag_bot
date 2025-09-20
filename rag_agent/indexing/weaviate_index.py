# rag_agent/indexing/weaviate_index.py
"""
Weaviate vector database indexing module

Safe upsert strategy:
1. safe_upsert_single_chunk(): safe upsert for individual chunk
   (check existence -> delete -> re-upsert)
2. upsert_chunks_with_vectors(safe_mode=True): batch processing in safe mode
3. bulk_upsert_by_doc_id(): bulk indexing by doc_id (delete by doc_id → re-upsert)

Usage examples:
    # safe individual upsert
    success = safe_upsert_single_chunk(chunk_item)

    # safe batch upsert (guaranteed vector update)
    count = upsert_chunks_with_vectors(chunks, safe_mode=True)

    # bulk indexing by doc_id (optimized performance)
    count = bulk_upsert_by_doc_id(chunks)
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Iterable, List

try:
    import weaviate
except Exception:
    weaviate = None

from app.core.config import settings  # Reuse backend settings

CLASS_NAME = "KBChunk"  # Recommended class name (separate from RAGDocument)
NAMESPACE = uuid.NAMESPACE_URL


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
    # v3: check existence in classes after schema.get()
    # (weaviate v4: separate function)
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
    chunk_uid(example: 'DOC123#45') → fixed UUID5
    - same chunk_uid always generates the same UUID
      → idempotent upsert guarantee
    """
    # uuid5 is stable UUID generation from string input
    return str(uuid.uuid5(NAMESPACE, chunk_uid))


def safe_upsert_single_chunk(
    item: Dict[str, Any],
    *,
    vector_key: str = "vector",
) -> bool:
    """
    Safe upsert for individual chunk: check existence
    -> delete -> re-upsert
    Processed outside of batch to guarantee vector update
    """
    c = _client()
    try:
        cu = item["chunk_uid"]
        uid = uuid_from_chunk_uid(cu)
        props = {
            "content": item["content"],
            "source": item.get("source"),
            "doc_id": item.get("doc_id"),
            "chunk_id": int(item.get("chunk_id", 0)),
            "page": item.get("page"),
            "chunk_uid": cu,
            "metadata_json": json.dumps(item.get("metadata", {}), ensure_ascii=False),
        }

        # 1. check existence → delete
        try:
            c.data_object.get_by_id(uid, class_name=CLASS_NAME)
            c.data_object.delete(uid, class_name=CLASS_NAME)
        except Exception:
            # if not exists, ignore
            pass

        # 2. re-upsert (include vector)
        c.data_object.create(
            data_object=props, class_name=CLASS_NAME, uuid=uid, vector=item[vector_key]
        )
        return True
    except Exception as e:
        print(f"Safe upsert failed for chunk_uid {cu}: {e}")
        return False
    finally:
        c.close()


def delete_chunks_by_doc_id(doc_id: str) -> int:
    """
    Delete all chunks for specific doc_id (for bulk indexing)
    """
    c = _client()
    try:
        # GraphQL where filter by doc_id
        where_filter = {"path": ["doc_id"], "operator": "Equal", "valueString": doc_id}

        result = c.batch.delete_objects(class_name=CLASS_NAME, where=where_filter)

        # return deleted object count
        return result.get("results", {}).get("successful", 0)
    except Exception as e:
        print(f"Delete by doc_id failed for {doc_id}: {e}")
        return 0
    finally:
        c.close()


def upsert_chunks_with_vectors(
    items: Iterable[Dict[str, Any]],
    *,
    vector_key: str = "vector",
    batch_size: int = 100,
    safe_mode: bool = False,
) -> int:
    """
    items: [{
      'chunk_uid', 'content', 'source', 'doc_id', 'chunk_id',
      'page', 'metadata' (dict), 'vector' (list[float])
    }, ...]
    - uuid derived from chunk_uid(uuid5) → idempotent

    Args:
        safe_mode: True means use safe upsert outside
        of batch (guaranteed vector update)
    """
    cnt = 0

    if safe_mode:
        # safe mode: process individually outside of batch
        for it in items:
            if safe_upsert_single_chunk(it, vector_key=vector_key):
                cnt += 1
        return cnt

    # existing batch mode (performance-first, limited vector update)
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
                # v3 client: same uuid add → merge-append
                # instead of fail if existing
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


def bulk_upsert_by_doc_id(
    items: Iterable[Dict[str, Any]],
    *,
    vector_key: str = "vector",
    batch_size: int = 100,
) -> int:
    """
    Bulk indexing by doc_id: delete existing chunks by doc_id → re-upsert
    Performance-optimized strategy (delete-by-doc_id → batch insert)
    """
    # group by doc_id
    doc_groups = {}
    for item in items:
        doc_id = item.get("doc_id", "unknown")
        if doc_id not in doc_groups:
            doc_groups[doc_id] = []
        doc_groups[doc_id].append(item)

    total_upserted = 0

    for doc_id, doc_items in doc_groups.items():
        # 1. delete all existing chunks for the doc_id
        deleted_count = delete_chunks_by_doc_id(doc_id)
        print(f"Deleted {deleted_count} existing chunks for doc_id: {doc_id}")

        # 2. batch insert new chunks
        c = _client()
        try:
            with c.batch as batch:
                batch.configure(batch_size=batch_size, timeout_retries=3)
                for item in doc_items:
                    cu = item["chunk_uid"]
                    uid = uuid_from_chunk_uid(cu)
                    props = {
                        "content": item["content"],
                        "source": item.get("source"),
                        "doc_id": item.get("doc_id"),
                        "chunk_id": int(item.get("chunk_id", 0)),
                        "page": item.get("page"),
                        "chunk_uid": cu,
                        "metadata_json": json.dumps(
                            item.get("metadata", {}), ensure_ascii=False
                        ),
                    }
                    c.batch.add_data_object(
                        data_object=props,
                        class_name=CLASS_NAME,
                        vector=item[vector_key],
                        uuid=uid,
                    )
                    total_upserted += 1
        finally:
            c.close()

    return total_upserted


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
