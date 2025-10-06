# rag_agent/retrieval/fuse.py
from __future__ import annotations

import math
from typing import Dict, List


def rrf_combine(
    result_lists: List[List[Dict]],
    score_keys: List[str] | None = None,
    weights: List[float] | None = None,
    *,
    c: int = 60,
    k: int | None = None,  # backward-compat (ignored; use c)
) -> List[Dict]:
    """
    Rank-based Reciprocal Rank Fusion (RRF) with weights.
    - result_lists: [ [ {chunk_uid, score_x}, ...], [ ... ] ]
    - score_keys:   ["score_bm25", "score_vec"] (keys per list)
    - weights:      [w1, w2] (defaults to 1.0)
    Returns list with 'score_rrf' populated and sorted desc.
    """
    weights = weights or [1.0] * len(result_lists)
    uid2best: Dict[str, Dict] = {}
    for li, results in enumerate(result_lists):
        # rank within each list by provided score key (desc)
        sk = None
        if score_keys and li < len(score_keys):
            sk = score_keys[li]
        ranked = results
        if sk is not None:
            try:
                ranked = sorted(results, key=lambda x: -float(x.get(sk, 0.0)))
            except Exception:
                ranked = results[:]
        for r, item in enumerate(ranked, 1):
            uid = item["chunk_uid"]
            contrib = float(weights[li]) / (float(c) + float(r))
            if uid not in uid2best:
                uid2best[uid] = {"proto": item.copy(), "score_rrf": 0.0}
            uid2best[uid]["score_rrf"] += contrib
    fused: List[Dict] = []
    for uid, pack in uid2best.items():
        p = pack["proto"]
        p["score_rrf"] = pack["score_rrf"]
        fused.append(p)
    fused.sort(key=lambda x: -float(x.get("score_rrf", 0.0)))
    return fused


def _zscore(vals: List[float]) -> List[float]:
    if not vals:
        return []
    n = float(len(vals))
    mu = sum(vals) / n
    var = sum((v - mu) ** 2 for v in vals) / n
    sd = (var**0.5) or 1.0
    return [(v - mu) / sd for v in vals]


def score_fuse(
    bm25_list: List[Dict],
    vec_list: List[Dict],
    *,
    w_bm25: float = 0.2,
    w_vec: float = 0.8,
) -> List[Dict]:
    """
    Score-based fusion with per-list z-score normalization.
    Returns fused list sorted by 'score_fused'.
    """
    # Collect raw scores
    bm_scores = [
        float(it.get("score_bm25", it.get("bm25", 0.0)) or 0.0) for it in bm25_list
    ]
    ve_scores = [float(it.get("score_vec", 0.0) or 0.0) for it in vec_list]
    bm_norm = _zscore(bm_scores) if bm_scores else []
    ve_norm = _zscore(ve_scores) if ve_scores else []

    uid2 = {}
    for it, s in zip(bm25_list, bm_norm):
        uid = it["chunk_uid"]
        uid2.setdefault(uid, {"proto": it.copy(), "bm": 0.0, "ve": 0.0})
        uid2[uid]["bm"] = float(s)
    for it, s in zip(vec_list, ve_norm):
        uid = it["chunk_uid"]
        uid2.setdefault(uid, {"proto": it.copy(), "bm": 0.0, "ve": 0.0})
        uid2[uid]["ve"] = float(s)

    fused: List[Dict] = []
    for uid, p in uid2.items():
        d = p["proto"].copy()
        d["score_fused"] = w_bm25 * p["bm"] + w_vec * p["ve"]
        fused.append(d)
    fused.sort(key=lambda x: -float(x.get("score_fused", 0.0)))
    return fused


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
