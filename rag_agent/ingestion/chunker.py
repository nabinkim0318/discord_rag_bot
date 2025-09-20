# rag_agent/ingestion/chunker.py
from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ===== Basic Idea =====
# 1) Split into paragraphs and then sentences
# 2) If paragraph is too long, pack it safely into sentences
# 3) Implement sliding window (overlap, char-based) aligned with sentence boundaries
# 4) Merge too short chunks with neighbors (auto-adjust)
# 5) start_char / end_char is guaranteed to be the offset based on the original text


@dataclass
class Chunk:
    chunk_id: int
    text: str
    start_char: int
    end_char: int
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "meta": self.meta,
        }


# ---------- Utility: Sentence Splitter Selection (Order: spaCy
# → NLTK → Regex) ----------
def _get_sentence_spans(text: str) -> List[Tuple[int, int]]:
    """
    Return list of sentence boundaries (start_char, end_char).
    Try spaCy(en_core_web_sm) → NLTK punkt → simple regex in order.
    """
    # 1) spaCy
    try:
        import spacy

        try:
            nlp = spacy.load("en_core_web_sm", disable=["ner", "tagger", "lemmatizer"])
        except Exception:
            # Consider model not installed environment:
            # English general Rule-based sentencizer
            nlp = spacy.blank("en")
            if "sentencizer" not in nlp.pipe_names:
                nlp.add_pipe("sentencizer")
        doc = nlp(text)
        return [(s.start_char, s.end_char) for s in doc.sents if s.text.strip()]
    except Exception:
        pass

    # 2) NLTK punkt
    try:
        import nltk
        from nltk.tokenize.punkt import PunktSentenceTokenizer

        try:
            # punkt may not be installed, so request download
            # (fallback to regex if fails)
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            try:
                nltk.download("punkt", quiet=True)
            except Exception:
                pass
        tokenizer = PunktSentenceTokenizer()
        spans = list(tokenizer.span_tokenize(text))
        return [(s, e) for (s, e) in spans if text[s:e].strip()]
    except Exception:
        pass

    # 3) Simple regex split (period/question/exclamation + space/newline)
    spans: List[Tuple[int, int]] = []
    start = 0
    for m in re.finditer(r"([.!?]+)(\s+|\Z)", text, flags=re.MULTILINE):
        end = m.end()
        seg = text[start:end].strip()
        if seg:
            # Calculate trim index based on the original text to ensure
            # the offset doesn't change due to leading/trailing whitespace removal
            # (simplification: here we slice the original text without strip)
            spans.append((start, end))
        start = end
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def _split_paragraph_spans(text: str) -> List[Tuple[int, int]]:
    """
    Return paragraph boundaries (start, end) based on empty lines (2 or more newlines).
    """
    spans: List[Tuple[int, int]] = []
    pos = 0
    # Two or more spaces as paragraph boundaries
    for m in re.finditer(r"\n\s*\n+", text):
        end = m.start()
        if end > pos:
            spans.append((pos, end))
        pos = m.end()
    if pos < len(text):
        spans.append((pos, len(text)))
    # Inside the paragraph, leading/trailing
    # whitespace is kept to maintain
    # offset accuracy
    return spans


def _collapse_whitespace(s: str) -> str:
    # Assume most normalization is done in the first step,
    # but add a safety measure for additional compression
    # (Note: start/end offset is based on the original text,
    # so only chunk.text is compressed)
    return re.sub(r"[ \t]+", " ", re.sub(r"[ \t]*\n[ \t]*", "\n", s)).strip()


# ---------- Core: Chunking ----------
def chunk_text(
    text: str,
    *,
    max_chars: int = 600,
    overlap: int = 150,
    section_path: Optional[str] = None,
    base_meta: Optional[Dict[str, Any]] = None,
    min_chunk_chars: Optional[int] = None,
    doc_id: Optional[str] = None,
    source: Optional[str] = None,
    page: Optional[int] = None,
) -> List[Chunk]:
    """
    Meaningful unit chunking (paragraph → sentence) + sliding window
    (overlap) concurrently.

    - If paragraph is less than or equal to max_chars, pass.
    - If exceeds, pack it into sentence boundaries.
    - Overlap between chunks is implemented based on
    'sentence boundaries + char-based'.
    - Merge too short chunks with neighbors.

    Return: List of Chunk (chunk_id, text, start_char,
    end_char, meta)
    """
    assert max_chars > 100 and overlap >= 0 and overlap < max_chars, "invalid sizes"

    if min_chunk_chars is None:
        # Default: merge candidates if less than 1/3 of the maximum size
        min_chunk_chars = max(120, int(max_chars / 3))

    para_spans = _split_paragraph_spans(text)
    chunks: List[Tuple[int, int]] = []  # (start, end) original text offset storage

    for p_start, p_end in para_spans:
        plen = p_end - p_start
        if plen <= max_chars:
            # Pass as is
            chunks.append((p_start, p_end))
            continue

        # Pack based on sentence boundaries
        sent_spans = [
            (s, e) for (s, e) in _get_sentence_spans(text[p_start:p_end])
        ]  # Paragraph slice based on
        # Convert to document-wide offset
        sent_spans = [(p_start + s, p_start + e) for (s, e) in sent_spans if e - s > 0]

        if not sent_spans:
            # If sentence boundaries are not found, hard slice
            _start = p_start
            while _start < p_end:
                _end = min(_start + max_chars, p_end)
                chunks.append((_start, _end))
                _start = max(_start + max_chars - overlap, _start + 1)
            continue

        # Slide sentence window
        i = 0
        n = len(sent_spans)
        while i < n:
            # Expand to the sentence that doesn't exceed max_chars starting from i
            window_start_char = sent_spans[i][0]
            j = i
            current_end_char = sent_spans[i][1]
            while j < n:
                s, e = sent_spans[j]
                if e - window_start_char <= max_chars:
                    current_end_char = e
                    j += 1
                else:
                    break
            # Include at least one sentence
            chunks.append((window_start_char, current_end_char))

            if current_end_char >= p_end:
                break

            # Next start considering overlap: previous chunk end - overlap
            next_start_char = max(window_start_char, current_end_char - overlap)

            # First sentence index greater than or equal to next_start_char
            next_i = j
            # Adjust boundaries back a little to match overlap
            # (next_start_char보다 start가 큰 첫 문장)
            for k in range(i + 1, j):
                if sent_spans[k][0] >= next_start_char:
                    next_i = k
                    break

            if next_i == i:
                next_i = i + 1  # Prevent infinite loop

            i = next_i

    # ----- Merge too short chunks (combine with previous/next) -----
    merged: List[Tuple[int, int]] = []
    for start, end in chunks:
        if not merged:
            merged.append((start, end))
            continue
        prev_s, prev_e = merged[-1]
        if (end - start) < min_chunk_chars:
            # If the end is too short, combine with the previous,
            # but allow up to max_chars * 1.5 (flexibility)
            if (end - prev_s) <= int(max_chars * 1.5):
                merged[-1] = (prev_s, end)
            else:
                merged.append((start, end))
        else:
            merged.append((start, end))

    # Final Chunk objectification + meta attachment
    out: List[Chunk] = []
    for idx, (s, e) in enumerate(merged):
        raw = text[s:e]
        cleaned = _collapse_whitespace(
            raw
        )  # Clean up for display purposes (offset invariant)
        meta = {
            "chunk_id": idx,
            "start_char": s,
            "end_char": e,
            "section_path": section_path,
            "doc_id": doc_id,
            "source": source,
            "page": page,
        }
        if base_meta:
            meta.update(base_meta)
        out.append(
            Chunk(
                chunk_id=idx,
                text=cleaned,
                start_char=s,
                end_char=e,
                meta=meta,
            )
        )
    return out


# ---------- Report/Validation Utility ----------
def summarize_chunks(chunks: List[Chunk], sample: int = 3) -> Dict[str, Any]:
    lengths = [len(c.text) for c in chunks]
    if not lengths:
        return {"count": 0, "avg": 0, "p50": 0, "p95": 0, "samples": []}
    lengths_sorted = sorted(lengths)
    p50 = statistics.median(lengths_sorted)
    p95 = lengths_sorted[
        min(len(lengths_sorted) - 1, math.floor(0.95 * len(lengths_sorted)))
    ]
    samples = []
    for c in chunks[:sample]:
        samples.append(
            {
                "chunk_id": c.chunk_id,
                "chars": len(c.text),
                "preview": c.text[:200].replace("\n", " ")
                + ("..." if len(c.text) > 200 else ""),
                "section_path": c.meta.get("section_path"),
                "page": c.meta.get("page"),
            }
        )
    return {
        "count": len(chunks),
        "avg": round(sum(lengths) / len(lengths), 1),
        "p50": int(p50),
        "p95": int(p95),
        "min": min(lengths),
        "max": max(lengths),
        "samples": samples,
    }
