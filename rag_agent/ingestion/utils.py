# rag_agent/ingestion/utils.py
from __future__ import annotations

import hashlib
import re
from pathlib import Path


def sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def sha1_text_compact(s: str) -> str:
    """Remove all whitespace, lowercase, then sha1 (prevent duplicate due to layout)"""
    compact = re.sub(r"\s+", "", s).lower()
    return hashlib.sha1(compact.encode("utf-8")).hexdigest()


def safe_stem(path: str | Path) -> str:
    p = Path(path)
    return p.stem


def guess_title_from_filename(path: str | Path) -> str:
    stem = safe_stem(path)
    # "AI_Bootcamp_Journey" -> "AI Bootcamp Journey"
    title = re.sub(r"[_\-]+", " ", stem).strip()[:200]
    return title
