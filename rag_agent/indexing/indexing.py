# rag_agent/indexing/embeddings.py
from __future__ import annotations

import hashlib
import math
import os
import random
from typing import List, Optional

# Options:
# 1) OpenAI (env: OPENAI_API_KEY) + text-embedding-3-small (assume English)
# 2) Local replacement (free): Hash-based pseudo-embedding (for testing/development)

_OPENAI_READY = False
try:
    import openai  # openai>=1.*

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


def embed_texts(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """
    Default: use text-embedding-3-small if OpenAI is available,
    otherwise use pseudo-embedding.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if _OPENAI_READY and api_key:
        openai.api_key = api_key
        mdl = model or "text-embedding-3-small"
        # openai>=1.* example (responses API instead of embeddings)
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        res = client.embeddings.create(model=mdl, input=texts)
        return [d.embedding for d in res.data]
    else:
        # Local replacement
        return [_pseudo_embed(t) for t in texts]
