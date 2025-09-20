# rag_agent/evaluation/metrics.py
from __future__ import annotations

import math
from typing import List, Sequence, Set

# --- Rank-based Utils ---


def precision_at_k(ranked_uids: Sequence[str], relevant: Set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    k = min(k, len(ranked_uids))
    hit = sum(1 for uid in ranked_uids[:k] if uid in relevant)
    return hit / k


def recall_at_k(ranked_uids: Sequence[str], relevant: Set[str], k: int) -> float:
    if not relevant:
        return 0.0
    k = min(k, len(ranked_uids))
    hit = sum(1 for uid in ranked_uids[:k] if uid in relevant)
    return hit / len(relevant)


def ap_at_k(ranked_uids: Sequence[str], relevant: Set[str], k: int) -> float:
    """Average Precision@k"""
    if not relevant:
        return 0.0
    k = min(k, len(ranked_uids))
    score = 0.0
    hit = 0
    for i in range(k):
        if ranked_uids[i] in relevant:
            hit += 1
            score += hit / (i + 1)
    return score / min(len(relevant), k)


def map_at_k(
    list_of_ranked: List[Sequence[str]], list_of_relevant: List[Set[str]], k: int
) -> float:
    if not list_of_ranked:
        return 0.0
    vals = [ap_at_k(r, rel, k) for r, rel in zip(list_of_ranked, list_of_relevant)]
    return sum(vals) / len(vals)


def mrr_at_k(ranked_uids: Sequence[str], relevant: Set[str], k: int) -> float:
    k = min(k, len(ranked_uids))
    for i in range(k):
        if ranked_uids[i] in relevant:
            return 1.0 / (i + 1)
    return 0.0


# --- nDCG ---
def dcg_at_k(gains: Sequence[int], k: int) -> float:
    k = min(k, len(gains))
    if k == 0:
        return 0.0
    return gains[0] + sum(gains[i] / math.log2(i + 2) for i in range(1, k))


def ndcg_at_k(ranked_uids: Sequence[str], relevant: Set[str], k: int) -> float:
    gains = [1 if uid in relevant else 0 for uid in ranked_uids]
    ideal = sorted(gains, reverse=True)
    dcg = dcg_at_k(gains, k)
    idcg = dcg_at_k(ideal, k)
    return dcg / idcg if idcg > 0 else 0.0
