from __future__ import annotations

from typing import Dict, List, Optional

try:
    from sentence_transformers import CrossEncoder  # type: ignore
except Exception:  # pragma: no cover - optional dep
    CrossEncoder = None


_MODEL_CACHE: Dict[str, "CrossEncoder"] = {}


def get_cross_encoder(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    if CrossEncoder is None:
        raise RuntimeError("sentence-transformers가 설치되어 있지 않습니다.")
    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = CrossEncoder(model_name)
    return _MODEL_CACHE[model_name]


def rerank_cross_encoder(
    query: str,
    candidates: List[Dict],
    *,
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    text_key: str = "content",
    top_k: Optional[int] = None,
) -> List[Dict]:
    """
    candidates: [{"content": ..., "chunk_uid": ..., ...}, ...]
    반환: score_ce 필드로 재정렬된 리스트
    """
    if not candidates:
        return []

    ce = get_cross_encoder(model_name)
    pairs = [(query, c.get(text_key, "") or "") for c in candidates]
    scores = ce.predict(pairs)

    rescored: List[Dict] = []
    for c, s in zip(candidates, scores):
        cc = dict(c)
        cc["score_ce"] = float(s)
        rescored.append(cc)

    rescored.sort(key=lambda x: x["score_ce"], reverse=True)
    return rescored[:top_k] if top_k else rescored
