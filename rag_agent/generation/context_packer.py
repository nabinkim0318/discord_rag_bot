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
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from app.core.config import settings
from app.core.logging import logger

# Load environment variables from root .env file
root_dir = Path(__file__).parent.parent.parent.parent
env_path = root_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)


# add path to backend directory
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    import tiktoken
except Exception:
    tiktoken = None
STOP = set(
    (
        "the",
        "a",
        "an",
        "and",
        "or",
        "is",
        "are",
        "to",
        "for",
        "of",
        "in",
        "on",
        "at",
        "by",
    )
)


def _dedup_key(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    toks = [w for w in re.sub(r"\s+", " ", s).strip().split(" ") if w and w not in STOP]
    return " ".join(toks[:40])  # 앞부분 40토큰까지만


def _soft_trim(text: str, max_chars: int = 1200) -> str:
    return (
        text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + "..."
    )


def pack_contexts(
    hits: List[Dict[str, Any]],
    *,
    prompt_header_tokens: int = 600,
    max_budget: Optional[int] = None,
    model_hint: str = "gpt-4o-mini",
    per_source_cap: int = 3,  # ✅ prevent source bias
    min_tail_budget: int = 256,  # ✅ answer margin tokens
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    budget = max_budget or settings.PROMPT_TOKEN_BUDGET
    # header + answer margin tokens
    remain = max(min_tail_budget, budget - prompt_header_tokens - min_tail_budget)
    remain = max(128, remain)

    # sort by score (rerank_score > score)
    def _score(h):
        rs = h.get("rerank_score")
        return rs if rs is not None else h.get("score", 0.0)

    sorted_hits = sorted(hits, key=_score, reverse=True)

    chosen, seen, per_src, total_tokens = [], set(), defaultdict(int), 0
    for h in sorted_hits:
        txt = (h.get("text") or h.get("content") or "").strip()
        if not txt:
            continue

        # too long chunk softcut
        txt = _soft_trim(txt, 1200)
        key = _dedup_key(txt[:600])
        if key in seen:
            continue

        src = h.get("source") or "unknown"
        if per_src[src] >= per_source_cap:
            continue

        tok = count_tokens(txt, model_hint)
        if total_tokens + tok > remain:
            continue

        h = dict(h)  # original preserve
        h["text"] = txt
        chosen.append(h)
        total_tokens += tok
        seen.add(key)
        per_src[src] += 1

        # even if budget is generous, leave 1~2 chunks in tail budget
        if remain - total_tokens < min_tail_budget:
            break

    meta = {
        "budget": budget,
        "prompt_header_tokens": prompt_header_tokens,
        "used_tokens_context": total_tokens,
        "num_contexts": len(chosen),
        "per_source_cap": per_source_cap,
        "min_tail_budget": min_tail_budget,
    }
    logger.debug(f"Context packed: {meta}")
    return chosen, meta


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
