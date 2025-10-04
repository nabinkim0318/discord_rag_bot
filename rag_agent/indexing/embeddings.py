# rag_agent/indexing/embeddings.py
from __future__ import annotations

import hashlib
import logging
import math
import os
import random
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Options:
# 1) OpenAI (env: OPENAI_API_KEY) + text-embedding-3-small (assume English)
# 2) Local replacement (free): Hash-based pseudo-embedding (for testing/development)

log = logging.getLogger(__name__)

# ── .env: Load repo root only once (match other files)
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

# OpenAI SDK 1.x availability check
_OPENAI_READY = False
try:
    from openai import OpenAI  # openai>=1.*

    _OPENAI_READY = True
except Exception:
    _OPENAI_READY = False


def _pseudo_embed(s: str, dim: int = 384) -> List[float]:
    """Reproducible vector without external API (for testing/development)."""
    h = hashlib.sha1(s.encode("utf-8")).digest()
    rng = random.Random(h)  # seed fixed
    v = [rng.uniform(-1, 1) for _ in range(dim)]
    # L2 normalize
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def _openai_client() -> Optional[OpenAI]:
    if not _OPENAI_READY:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL") or None  # compatible endpoint support
    try:
        return OpenAI(api_key=api_key, base_url=base_url)
    except Exception as e:
        log.warning(f"[embeddings] OpenAI client init failed: {e}")
        return None


def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """
    Priority:
    1) OpenAI(or compatible) API +
    selected model/basic model(text-embedding-3-small)
    2) Local replacement pseudo-embedding(for testing/development)
    """
    cli = _openai_client()
    if cli:
        mdl = model or os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
        try:
            res = cli.embeddings.create(model=mdl, input=texts)
            return [d.embedding for d in res.data]
        except Exception as e:
            log.warning(f"[embeddings] API call failed, falling back to pseudo: {e}")

    # Fallback
    return [_pseudo_embed(t) for t in texts]
