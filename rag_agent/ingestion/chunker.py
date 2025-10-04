# rag_agent/ingestion/chunker.py
# ===== Basic Idea =====
# 1) Split into paragraphs and then sentences
# 2) If paragraph is too long, pack it safely into sentences
# 3) Implement sliding window (overlap, char-based) aligned with sentence boundaries
# 4) Merge too short chunks with neighbors (auto-adjust)
# 5) start_char / end_char is guaranteed to be the offset based on the original text
# rag_agent/ingestion/chunker.py
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# --- sentence tokenizer: use spaCy if available, use NLTK if
# available, use regex fallback ---

# Global spaCy model cache to avoid repeated loading
_NLP = None


def _sent_tokenize(text: str) -> List[Tuple[int, int]]:
    """
    Return list of (start_char, end_char) spans for sentences.
    """
    try:
        import spacy

        global _NLP

        # Load model only once and cache it
        if _NLP is None:
            _NLP = spacy.load("en_core_web_sm", disable=["tagger", "ner", "lemmatizer"])

        doc = _NLP(text)
        return [(s.start_char, s.end_char) for s in doc.sents]
    except Exception:
        try:
            from nltk.tokenize import PunktSentenceTokenizer

            # assume downloaded
            tok = PunktSentenceTokenizer()
            spans = list(tok.span_tokenize(text))
            return spans
        except Exception:
            # simple fallback: based on period/newline
            spans = []
            start = 0
            for m in re.finditer(r"[^\S\r\n]*[\.\!\?]\s+|\n{2,}", text):
                end = m.end()
                if end > start:
                    spans.append((start, end))
                    start = end
            if start < len(text):
                spans.append((start, len(text)))
            return spans


@dataclass
class Chunk:
    text: str
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "meta": self.meta}


def _merge_short_spans(
    spans: List[Tuple[int, int]], min_chars: int
) -> List[Tuple[int, int]]:
    if not spans:
        return spans
    out = [list(spans[0])]
    for s, e in spans[1:]:
        if (out[-1][1] - out[-1][0]) < min_chars:
            # merge with previous
            out[-1][1] = e
        else:
            out.append([s, e])
    return [tuple(x) for x in out]


def _split_long(text: str, s: int, e: int, max_chars: int) -> List[Tuple[int, int]]:
    # if too long, cut near whitespace
    spans = []
    i = s
    while i < e:
        j = min(i + max_chars, e)
        if j < e:
            # search backward for whitespace with proper reverse index handling
            rev = text[i:j][::-1]
            m = re.search(r"\s", rev)
            if m:
                # Fix: Proper reverse index calculation with safety bounds
                cut = max(i + 1, j - m.start() - 1)  # Ensure progress
            else:
                cut = j
            # Safety check to prevent infinite loop
            if cut <= i:
                cut = min(j, i + max_chars)
            spans.append((i, cut))
            i = cut
        else:
            spans.append((i, e))
            break
    return spans


def _paragraph_spans(text: str) -> List[Tuple[int, int]]:
    # assume two or more empty lines as paragraph boundaries
    spans = []
    last = 0
    for m in re.finditer(r"\n{2,}", text):
        s, e = m.span()
        if s > last:
            spans.append((last, s))
        last = e
    if last < len(text):
        spans.append((last, len(text)))
    return spans


def _build_windows(
    unit_spans: List[Tuple[int, int]], max_chars: int, overlap: int
) -> List[Tuple[int, int]]:
    # Fix: Handle empty input
    if not unit_spans:
        return []

    out = []
    cur_s = unit_spans[0][0]
    cur_e = cur_s
    i = 0
    while i < len(unit_spans):
        s, e = unit_spans[i]
        if (e - cur_s) <= max_chars:
            cur_e = e
            i += 1
            if i == len(unit_spans):
                out.append((cur_s, cur_e))
        else:
            # if window overflows, cut and apply overlap
            cut_e = max(cur_s + max_chars, cur_e)
            out.append((cur_s, cut_e))
            cur_s = max(cut_e - overlap, s)
            cur_e = cur_s
    return out


def _char_stats(lengths: List[int]) -> Dict[str, float]:
    if not lengths:
        return {"count": 0}
    arr = sorted(lengths)
    n = len(arr)
    median = arr[n // 2] if n % 2 == 1 else (arr[n // 2 - 1] + arr[n // 2]) / 2
    p10 = arr[max(0, int(0.10 * n) - 1)]
    p90 = arr[min(n - 1, int(0.90 * n) - 1)]
    return {
        "count": n,
        "mean": sum(arr) / n,
        "median": median,
        "p10": p10,
        "p90": p90,
        "min": arr[0],
        "max": arr[-1],
    }


def chunk_text(
    text: str,
    *,
    max_chars: int = 1000,
    overlap: int = 200,
    min_chunk_chars: int = 200,
    section_path: Optional[str] = None,
    base_meta: Optional[Dict[str, Any]] = None,
    doc_id: Optional[str] = None,
    source: Optional[str] = None,
    page: Optional[int] = None,
) -> List[Chunk]:
    """
    Paragraph first -> merge sentences if needed -> window(overlap)
    - Each chunk meta: chunk_id, start_char, end_char, section_path,
    doc_id, source, page
    - Merge with neighbors if too short, safe split if too long
    """
    base_meta = dict(base_meta or {})
    paras = _paragraph_spans(text) or [(0, len(text))]
    # if paragraph is too short, merge with neighbor sentences safely
    merged: List[Tuple[int, int]] = []
    for s, e in paras:
        if (e - s) < min_chunk_chars:
            merged.append((s, e))
            continue
        # split into sentences and merge short sentences
        # Fix: Convert slice-based offsets to original text offsets
        sent_spans = [(s + ss, s + ee) for (ss, ee) in _sent_tokenize(text[s:e])]
        if not sent_spans:
            merged.append((s, e))
            continue
        sent_spans = _merge_short_spans(sent_spans, min_chunk_chars // 2)
        # if too long, split
        tmp = []
        for ss, ee in sent_spans:
            if (ee - ss) > max_chars:
                tmp.extend(_split_long(text, ss, ee, max_chars))
            else:
                tmp.append((ss, ee))
        merged.extend(tmp)

    # final chunk boundaries with sliding window
    unit_spans = merged if merged else [(0, len(text))]
    windows = _build_windows(unit_spans, max_chars=max_chars, overlap=overlap)

    chunks: List[Chunk] = []
    for idx, (s, e) in enumerate(windows):
        ch_text = text[s:e].strip()
        if not ch_text:
            continue
        meta = {
            **base_meta,
            "doc_id": doc_id,
            "source": source,
            "page": page,
            "section_path": section_path,
            "chunk_id": idx,
            "start_char": s,
            "end_char": e,
        }
        chunks.append(Chunk(text=ch_text, meta=meta))

    # distribution log & sample 3
    lens = [len(c.text) for c in chunks]
    st = _char_stats(lens)
    log.info(
        "[chunker] produced %d chunks \
        (chars mean=%.1f, p10=%d, p90=%d, min=%d, max=%d)",
        st.get("count", 0),
        st.get("mean", 0.0),
        st.get("p10", 0),
        st.get("p90", 0),
        st.get("min", 0),
        st.get("max", 0),
    )
    for i in range(min(3, len(chunks))):
        t = chunks[i].text
        log.info(
            "[chunker] sample#%d: %s", i, (t[:220] + ("…" if len(t) > 220 else ""))
        )

    return chunks


def validate_chunk_data(chunks: List[Chunk], original_text: str) -> Dict[str, Any]:
    """
    Validate chunk data integrity and statistics

    Args:
        chunks: List of chunks to validate
        original_text: Original text for offset validation

    Returns:
        Dict with validation results and statistics
    """
    validation_results = {
        "offset_integrity_passed": True,
        "id_stability_passed": True,
        "length_stats": {},
        "integration_check_passed": True,
        "errors": [],
    }

    # 1. Offset integrity check
    for i, chunk in enumerate(chunks):
        start_char = chunk.meta.get("start_char", 0)
        end_char = chunk.meta.get("end_char", len(chunk.text))

        try:
            original_slice = original_text[start_char:end_char]
            assert (
                chunk.text.strip() == original_slice.strip()
            ), f"Chunk {i}: text mismatch at offset {start_char}:{end_char}"
        except (AssertionError, IndexError) as e:
            validation_results["offset_integrity_passed"] = False
            validation_results["errors"].append(
                f"Offset integrity error in chunk {i}: {str(e)}"
            )

    # 2. Length statistics
    chunk_lengths = [len(chunk.text) for chunk in chunks]
    if chunk_lengths:
        sorted_lengths = sorted(chunk_lengths)
        n = len(sorted_lengths)
        p10 = sorted_lengths[max(0, int(0.10 * n) - 1)]
        p90 = sorted_lengths[min(n - 1, int(0.90 * n) - 1)]
        mean_length = sum(chunk_lengths) / len(chunk_lengths)
        min_length = min(chunk_lengths)
        max_length = max(chunk_lengths)

        validation_results["length_stats"] = {
            "count": len(chunk_lengths),
            "mean": mean_length,
            "p10": p10,
            "p90": p90,
            "min": min_length,
            "max": max_length,
            "p10_p90_in_range": 300 <= p10 and p90 <= 1000,
        }

        # Check if p10/p90 are in expected range (300-1000 chars)
        if not (300 <= p10 and p90 <= 1000):
            validation_results["errors"].append(
                f"Length stats out of range: p10={p10}, p90={p90}"
            )

    # 3. Integration check - verify required fields for hybrid indexer
    required_fields = ["doc_id", "chunk_id", "source", "page", "section_path"]
    for i, chunk in enumerate(chunks):
        missing_fields = [field for field in required_fields if field not in chunk.meta]
        if missing_fields:
            validation_results["integration_check_passed"] = False
            validation_results["errors"].append(
                f"Chunk {i} missing required fields: {missing_fields}"
            )

    return validation_results


def test_id_stability(chunker_func, text: str, **kwargs) -> bool:
    """
    Test ID stability by running chunker twice and comparing chunk_uid sets

    Args:
        chunker_func: Chunking function to test
        text: Input text
        **kwargs: Additional arguments for chunker

    Returns:
        bool: True if IDs are stable, False otherwise
    """
    # Run chunker twice
    chunks1 = chunker_func(text, **kwargs)
    chunks2 = chunker_func(text, **kwargs)

    # Extract chunk_uid sets
    uids1 = {
        chunk.meta.get("chunk_uid", chunk.meta.get("chunk_id", "")) for chunk in chunks1
    }
    uids2 = {
        chunk.meta.get("chunk_uid", chunk.meta.get("chunk_id", "")) for chunk in chunks2
    }

    return uids1 == uids2


# chunks = chunk_text(
#     text,
#     max_chars=1000,
#     overlap=200,
#     section_path="1. Intro > 1.1 Overview",
#     base_meta={"ingested_at": "2025-09-19T12:00:00Z", "checksum": "sha1:..."},
#     doc_id="doc_bootcamp_journey",
#     source="AI Bootcamp Journey & Learning Path.pdf",
#     page=None,  # if page-based, put page number here
# )
