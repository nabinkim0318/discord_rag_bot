# rag_agent/ingestion/normalize.py
from __future__ import annotations

import re

_BULLET = r"(?:^[\s>*\-•◦▪●·\d]+\)|^[\s>*\-•◦▪●·]+)"  # simple bullet/number prefix
_URL = r"(https?://[^\s)]+)"
_EMOJI = r"[\U00010000-\U0010ffff]"  # extended emoji

HEADER_FOOTER_CANDIDATES = [
    r"^\s*AI\s+Bootcamp\s+.*$",  # document header pattern (example)
    r"^\s*Intern\s+FAQ\s+.*$",
    r"^\s*Training\s+For\s+AI\s+Engineer\s+Interns\s*$",
]
PAGE_NUMBER_PATTERNS = [
    r"^\s*\d+\s*$",  # only number in a line
    r"^\s*page\s*\d+\s*$",  # "Page 12"
    r"^\s*\d+\s*/\s*\d+\s*$",  # "12/52"
]


def strip_header_footer(lines: list[str]) -> list[str]:
    new = []
    for ln in lines:
        # remove page number/header/footer candidates
        if any(re.match(pat, ln.strip(), re.I) for pat in PAGE_NUMBER_PATTERNS):
            continue
        if any(re.match(pat, ln.strip(), re.I) for pat in HEADER_FOOTER_CANDIDATES):
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


def normalize_urls(s: str) -> str:
    # remove noise like parentheses/comma after URL
    s = re.sub(rf"{_URL}[\),\.]+", r"\1", s)
    return s


def remove_emojis(s: str) -> str:
    return re.sub(_EMOJI, "", s)


def normalize_text(raw: str) -> str:
    if not raw:
        return ""
    # 1) remove header/footer/page number (line by line)
    lines = raw.splitlines()
    lines = strip_header_footer(lines)
    s = "\n".join(lines)

    # 2) remove bullet
    s = remove_bullets(s)

    # 3) normalize URL
    s = normalize_urls(s)

    # 4) remove emoji/non-standard (optional)
    s = remove_emojis(s)

    # 5) collapse whitespace
    s = collapse_whitespace(s)
    return s
