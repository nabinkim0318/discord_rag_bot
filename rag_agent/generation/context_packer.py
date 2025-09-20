# rag_agent/generation/context_packer.py
"""
Summary: Get the most "useful" chunks within
PROMPT_TOKEN_BUDGET considering length, score, and duplication.

Basic strategy:

Rerank score (if available) or hybrid score for sorting

Near-duplicate sentences (Jaccard/simple similarity) minimized

Remaining budget sequentially filled

Token count is recommended to use tiktoken (fallback if not installed).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.config import settings
from app.core.logging import logger

# add path to backend directory
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    import tiktoken
except Exception:
    tiktoken = None


# Rough token count (fallback)
def _rough_token_count(text: str) -> int:
    # Rough token count based on English (roughly 1.3~1.5
    # words/token… conservatively char count/4)
    return max(1, len(text) // 4)


def count_tokens(text: str, model_hint: str = "gpt-4o-mini") -> int:
    if tiktoken is None:
        return _rough_token_count(text)
    try:
        enc = tiktoken.get_encoding("o200k_base")  # gpt-4o series
        return len(enc.encode(text))
    except Exception:
        return _rough_token_count(text)


def _dedup_key(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def pack_contexts(
    hits: List[Dict[str, Any]],
    *,
    prompt_header_tokens: int = 600,  # System + instruction + format margin
    max_budget: int = None,
    model_hint: str = "gpt-4o-mini",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    hits: [{text, chunk_uid, score, rerank_score? , source, page, ...}]
    Return: (selected hits, packing metadata)
    """
    budget = max_budget or settings.PROMPT_TOKEN_BUDGET
    remain = max(256, budget - prompt_header_tokens)
    chosen: List[Dict[str, Any]] = []

    # Sort: rerank_score first, then score
    def _score(h):
        if "rerank_score" in h and h["rerank_score"] is not None:
            return h["rerank_score"]
        return h.get("score", 0.0)

    sorted_hits = sorted(hits, key=_score, reverse=True)

    # Simple deduplication: filter near-duplicates with key set
    seen = set()
    total_tokens = 0
    for h in sorted_hits:
        text = h.get("text") or h.get("content", "")
        key = _dedup_key(text[:500])
        if key in seen:
            continue
        tok = count_tokens(text, model_hint)
        if total_tokens + tok > remain:
            continue
        chosen.append(h)
        total_tokens += tok
        seen.add(key)

    meta = {
        "budget": budget,
        "prompt_header_tokens": prompt_header_tokens,
        "used_tokens_context": total_tokens,
        "num_contexts": len(chosen),
    }
    logger.debug(f"Context packed: {meta}")
    return chosen, meta


def render_context_block(chosen: List[Dict[str, Any]]) -> str:
    """
    Construct context block string for prompt
    """
    lines = []
    for i, h in enumerate(chosen, 1):
        src = h.get("source", "")
        pg = h.get("page", "")
        uid = h.get("chunk_uid", "")
        lines.append(f"[{i}] (src: {src}, page: " f"{pg}, uid: {uid})\n{h['text']}\n")
    return "\n".join(lines)
