# rag_agent/retrieval/vector.py
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.core.metrics import record_failure_metric
from rag_agent.indexing.embeddings import embed_texts

log = logging.getLogger(__name__)

try:
    import weaviate
except Exception:
    weaviate = None

CLASS_NAME = "KBChunk"


def _client():
    if weaviate is None:
        raise RuntimeError("weaviate is not installed")
    cfg = {"url": settings.WEAVIATE_URL}
    if getattr(settings, "WEAVIATE_API_KEY", None):
        cfg["auth_client_secret"] = weaviate.AuthApiKey(
            api_key=settings.WEAVIATE_API_KEY
        )
    return weaviate.Client(**cfg)


def vector_search(
    query: str,
    *,
    k: int = 25,
    filters: Optional[Dict[str, Any]] = None,
    embed_model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Weaviate near-vector search. Use external embedding.
    Return: [{chunk_uid, content, source, doc_id, chunk_id,
    page, score(float 0~1 approximate)}]
    """
    vec = embed_texts([query], model=embed_model)[0]
    where = None
    if filters:
        # Weaviate where filter (e.g. {"path":["doc_id"],
        # "operator":"Equal", "valueString":"..."} ...)
        where = filters

    c = _client()
    try:
        q = (
            c.query.get(
                CLASS_NAME,
                ["chunk_uid", "content", "source", "doc_id", "chunk_id", "page"],
            )
            .with_near_vector({"vector": vec})
            # distance/score is in _additional
            .with_additional(["distance", "certainty"])
            .with_limit(k)
        )
        if where:
            q = q.with_where(where)

        res = q.do()
        objs = res["data"]["Get"].get(CLASS_NAME) or []
        out: List[Dict[str, Any]] = []
        for o in objs:
            add = o.get("_additional") or {}
            # weaviate v3: cosine distance(0~2) or dot etc. depends
            # on backend settings
            # for now, use certainty(0~1) if available, otherwise 1
            # - distance approximate
            if "certainty" in add and add["certainty"] is not None:
                score = float(add["certainty"])
            else:
                dist = float(add.get("distance", 1.0))
                score = max(0.0, 1.0 - dist)
            out.append(
                {
                    "chunk_uid": o.get("chunk_uid"),
                    "content": o.get("content"),
                    "source": o.get("source"),
                    "doc_id": o.get("doc_id"),
                    "chunk_id": o.get("chunk_id"),
                    "page": o.get("page"),
                    "score_vec": score,
                }
            )
        return out
    except Exception as e:
        # record once at this level (can keep only upper level if desired)
        try:
            record_failure_metric("/api/v1/rag/retrieval", "weaviate_query_error")
        except Exception as e:
            log.exception("metric failure, %s", e)
            pass
        log.exception("weaviate vector query failed, %s", e)
        return []
    finally:
        c.close()
