# rag_agent/retrieval/fuse.py
from __future__ import annotations

import math
from typing import Dict, List


def rrf_combine(
    lists: List[List[Dict]],
    *,
    k: int = 60,
    score_keys: List[str] | None = None,
) -> List[Dict]:
    """
    Reciprocal Rank Fusion.
    lists: e.g. [bm25_results, vec_results]
    score_keys: score key to read from each list element (e.g. ["bm25","score_vec"]);
    if None, use rank-based only.
    """
    score_keys = score_keys or [None] * len(lists)
    agg: Dict[str, Dict] = {}
    for L, sk in zip(lists, score_keys):
        for rank, item in enumerate(L, start=1):
            uid = item["chunk_uid"]
            base = agg.get(uid, {"item": item, "rrf": 0.0})
            # basic RRF(rank) + optionally original score weighted (slightly)
            rrf = 1.0 / (k + rank)
            if sk and item.get(sk) is not None:
                # assume 0~1 score and fine addition (weight is empirical value)
                rrf += 0.05 * float(item[sk])
            base["rrf"] += rrf
            agg[uid] = base
    out = []
    for uid, pack in agg.items():
        it = dict(pack["item"])
        it["score_rrf"] = pack["rrf"]
        out.append(it)
    out.sort(key=lambda x: x["score_rrf"], reverse=True)
    return out


def cosine_sim(a: List[float], b: List[float]) -> float:
    da = math.sqrt(sum(x * x for x in a)) or 1.0
    db = math.sqrt(sum(x * x for x in b)) or 1.0
    return sum(x * y for x, y in zip(a, b)) / (da * db)


def mmr_select(
    items: List[Dict],
    *,
    lambda_: float = 0.6,
    topn: int = 10,
    text_key: str = "content",
) -> List[Dict]:
    """
    MMR: diversity correction.
    - similarity is simply approximated Jaccard similarity
    based on text (lightweight replacement)
    - for advanced, replace with cosine using each item embedding together.
    """
    if not items:
        return []

    def _token_set(s: str) -> set:
        return set(t.lower() for t in s.split())

    selected: List[Dict] = []
    candidate = items[:]
    rep_tokens = {}  # cache
    while candidate and len(selected) < topn:
        if not selected:
            selected.append(candidate.pop(0))
            continue
        best, best_score = None, -1e9
        for it in candidate:
            # relevance: use RRF score
            rel = float(it.get("score_rrf", 0.0))
            # diversity penalty: max_j sim(it, j)
            toks_i = rep_tokens.get(id(it))
            if toks_i is None:
                toks_i = _token_set(it.get(text_key, ""))
                rep_tokens[id(it)] = toks_i
            max_sim = 0.0
            for j in selected:
                toks_j = rep_tokens.get(id(j))
                if toks_j is None:
                    toks_j = _token_set(j.get(text_key, ""))
                    rep_tokens[id(j)] = toks_j
                # Jaccard approximation
                inter = len(toks_i & toks_j)
                union = len(toks_i | toks_j) or 1
                sim = inter / union
                if sim > max_sim:
                    max_sim = sim
            score = lambda_ * rel - (1 - lambda_) * max_sim
            if score > best_score:
                best, best_score = it, score
        selected.append(best)
        candidate.remove(best)
    return selected
