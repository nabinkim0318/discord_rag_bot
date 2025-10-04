# rag_agent/ingestion/normalize.py
from __future__ import annotations

import re
from typing import Iterable, Optional

_BULLET = r"(?:^[\s>*\-•◦▪●·\d]+\)|^[\s>*\-•◦▪●·]+)"  # simple bullet/number prefix
_NUMBERED_LIST = r"^\d+\.\s+"  # numbered list pattern (1. 2. 3.)
_URL = r"(https?://[^\s)]+)"
_EMOJI = r"[\U00010000-\U0010ffff]"  # extended emoji

DEFAULT_HEADER_FOOTER_CANDIDATES = [
    r"^\s*AI\s+Bootcamp\s+.*$",
    r"^\s*Intern\s+FAQ\s+.*$",
    r"^\s*Training\s+For\s+AI\s+Engineer\s+Interns\s*$",
]

PAGE_NUMBER_PATTERNS = [
    r"^\s*\d+\s*$",  # only number in a line
    r"^\s*page\s*\d+\s*$",  # "Page 12"
    r"^\s*\d+\s*/\s*\d+\s*$",  # "12/52"
]


def strip_header_footer(
    lines: list[str], header_footer_patterns: Optional[Iterable[str]] = None
) -> list[str]:
    hf = list(header_footer_patterns or DEFAULT_HEADER_FOOTER_CANDIDATES)
    new = []
    for ln in lines:
        s = ln.strip()
        if any(re.match(p, s, re.I) for p in PAGE_NUMBER_PATTERNS):
            continue
        if any(re.match(p, s, re.I) for p in hf):
            continue
        new.append(ln)
    return new


def collapse_whitespace(s: str) -> str:
    # collapse multiple whitespace in a paragraph -> one, remove trailing whitespace
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"[ \t]*\n[ \t]*", "\n", s)  # remove surrounding whitespace
    s = re.sub(r"\n{3,}", "\n\n", s)  # prevent more than 2 empty lines
    return s.strip()


def remove_bullets(s: str) -> str:
    # remove bullet/number prefix in a line
    lines = s.splitlines()
    cleaned = [re.sub(_BULLET, "", ln).strip() for ln in lines]
    return "\n".join(cleaned)


def remove_numbered_lists(s: str) -> str:
    # remove only numbered list patterns (1. 2. 3.) while preserving content
    lines = s.splitlines()
    cleaned = [re.sub(_NUMBERED_LIST, "", ln).strip() for ln in lines]
    return "\n".join(cleaned)


def normalize_urls(s: str) -> str:
    # remove noise like parentheses/comma after URL
    s = re.sub(rf"{_URL}[\),\.]+", r"\1", s)
    return s


def remove_emojis(s: str) -> str:
    return re.sub(_EMOJI, "", s)


def normalize_text(
    raw: str,
    *,
    header_footer_patterns: Optional[Iterable[str]] = None,
    remove_emoji: bool = True,
    remove_bullet: bool = True,
    remove_numbered_lists_only: bool = False,
) -> str:
    if not raw:
        return ""
    # 1) remove header/footer/page number (line by line)
    lines = raw.splitlines()
    lines = strip_header_footer(lines, header_footer_patterns)
    s = "\n".join(lines)

    # 2) remove bullet or numbered lists based on option
    if remove_numbered_lists_only:
        s = remove_numbered_lists(s)
    elif remove_bullet:
        s = remove_bullets(s)

    # 3) normalize URL
    s = normalize_urls(s)

    # 4) remove emoji/non-standard (optional)
    s = remove_emojis(s)

    # 5) collapse whitespace
    s = collapse_whitespace(s)
    return s
