# rag_agent/retrieval/reranker.py
from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import settings
from app.core.logging import logger


def _have_cohere():
    return bool(settings.COHERE_API_KEY)


def _have_jina():
    return bool(settings.JINA_API_KEY)


def rerank_with_cohere(query: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        import cohere

        client = cohere.Client(settings.COHERE_API_KEY)
        docs = [h["text"] for h in hits]
        resp = client.rerank(
            model="rerank-english-v3.0",
            query=query,
            documents=docs,
            top_n=len(docs),
            return_documents=False,
        )
        # resp.results[i].index, .relevance_score
        by_idx = {r.index: r.relevance_score for r in resp.results}
        for i, h in enumerate(hits):
            h["rerank_score"] = float(by_idx.get(i, 0.0))
        return sorted(hits, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
    except Exception as e:
        logger.warning(f"Cohere rerank failed: {e}")
        return hits


def rerank_with_jina(query: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        import requests

        url = "https://api.jina.ai/v1/rerank"
        headers = {"Authorization": f"Bearer {settings.JINA_API_KEY}"}
        payload = {
            "model": "jina-reranker-v1-base-en",
            "query": query,
            "documents": [h["text"] for h in hits],
            "top_n": len(hits),
        }
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        by_idx = {
            it["index"]: it.get("relevance_score", 0.0)
            for it in data.get("results", [])
        }
        for i, h in enumerate(hits):
            h["rerank_score"] = float(by_idx.get(i, 0.0))
        return sorted(hits, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
    except Exception as e:
        logger.warning(f"Jina rerank failed: {e}")
        return hits


def maybe_rerank(
    query: str, hits: List[Dict[str, Any]], method: str | None
) -> List[Dict[str, Any]]:
    """
    method: None | 'cohere' | 'jina'
    """
    if not method or not hits:
        return hits
    if method == "cohere" and _have_cohere():
        return rerank_with_cohere(query, hits)
    if method == "jina" and _have_jina():
        return rerank_with_jina(query, hits)
    return hits
