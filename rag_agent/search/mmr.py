# rag_agent/search/mmr.py
from __future__ import annotations

import math
from typing import Callable, List, Sequence


def cosine_sim(a: Sequence[float], b: Sequence[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(min(num / (na * nb), 1.0), -1.0)


def mmr_rerank(
    *,
    query_vec: Sequence[float],
    cand_vecs: List[Sequence[float]],
    cand_payloads: List[dict],
    k: int,
    lambda_: float = 0.65,  # relevance(closeness) weight
    sim: Callable[[Sequence[float], Sequence[float]], float] = cosine_sim,
) -> List[dict]:
    """
    Maximal Marginal Relevance:
      argmax_d [ λ * sim(q, d) - (1-λ) * max_{d' in S} sim(d, d') ]
    Return: selected cand_payloads list (length k)
    """
    n = len(cand_vecs)
    if n == 0 or k <= 0:
        return []

    # Pre-compute query and candidate similarities
    rel = [sim(query_vec, v) for v in cand_vecs]

    selected = []
    selected_idx = set()

    while len(selected) < min(k, n):
        best_i = None
        best_score = -1e9

        for i in range(n):
            if i in selected_idx:
                continue
            if not selected:
                score = rel[i]
            else:
                red = max(sim(cand_vecs[i], cand_vecs[j]) for j in selected_idx)
                score = lambda_ * rel[i] - (1.0 - lambda_) * red

            if score > best_score:
                best_score = score
                best_i = i

        selected_idx.add(best_i)
        selected.append(cand_payloads[best_i])

    return selected
