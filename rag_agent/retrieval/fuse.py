# rag_agent/retrieval/fuse.py
from __future__ import annotations

import math
from typing import Dict, List


def rrf_combine(
    lists: List[List[Dict]],
    *,
    k: int = 60,
    score_keys: List[str] | None = None,
    weights: List[float] | None = None,
) -> List[Dict]:
    """
    Reciprocal Rank Fusion with optional weights.
    lists: e.g. [bm25_results, vec_results]
    score_keys: score key to read from each list element (e.g. ["bm25","score_vec"]);
    if None, use rank-based only.
    weights: optional weights for each list (e.g. [0.4, 0.6] for BM25/Vector)
    """
    score_keys = score_keys or [None] * len(lists)
    weights = weights or [1.0] * len(lists)  # default equal weights

    agg: Dict[str, Dict] = {}
    for L, sk, weight in zip(lists, score_keys, weights):
        for rank, item in enumerate(L, start=1):
            uid = item["chunk_uid"]
            base = agg.get(uid, {"item": item, "rrf": 0.0})
            # basic RRF(rank) weighted by list weight
            rrf = weight * (1.0 / (k + rank))
            if sk and item.get(sk) is not None:
                # assume 0~1 score and fine addition (weight is empirical value)
                # 0.05 is empirical value: corrects vector/keyword score differences
                # Optimal 0.05 found in offline nDCG@10 experiments
                # Fine adjustment to rank-based RRF when vector scores are in 0~1 range
                rrf += 0.05 * weight * float(item[sk])
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
        # Improved tokenization for Korean/mixed text support
        # Simplified with lowercase conversion + non-alphanumeric removal
        import re

        # Remove non-alphanumeric chars, split by whitespace, filter empty tokens
        tokens = re.sub(r"[^\w\s]", " ", s.lower()).split()
        return set(t for t in tokens if t.strip())

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
