# rag_agent/retrieval/keyword.py
from __future__ import annotations

import re
from typing import Dict, List, Optional

from rag_agent.indexing.sqlite_fts import bm25_search as _bm25_search


def _make_highlights(
    text: str, query: str, max_snips: int = 2, window: int = 60
) -> List[str]:
    # very lightweight highlights: extract window around matching query terms
    terms = [t for t in re.split(r"\W+", query) if t]
    snips = []
    for t in terms:
        m = re.search(re.escape(t), text, re.I)
        if not m:
            continue
        s = max(0, m.start() - window)
        e = min(len(text), m.end() + window)
        snips.append(text[s:e].replace("\n", " "))
        if len(snips) >= max_snips:
            break
    return snips


def bm25_search(
    db_path: str, query: str, *, k: int = 25, where: Optional[str] = None
) -> List[Dict]:
    rows = _bm25_search(db_path, query, k=k, where=where)
    out = []
    for r in rows:
        out.append(
            {
                "chunk_uid": r["chunk_uid"],
                "content": r["text"],
                "source": r["source"],
                "doc_id": r["doc_id"],
                "chunk_id": r["chunk_id"],
                "page": r["page"],
                "title": r.get("title"),
                "section": r.get("section"),
                "score_bm25": float(r.get("bm25", 0.0)),
                "highlights": _make_highlights(r["text"], query),
            }
        )
    return out
