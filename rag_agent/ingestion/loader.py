# rag_agent/ingestion/loader.py
# load original documents from text, PDF, CSV, JSON, etc.
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import fitz  # pymupdf

from .normalize import normalize_text
from .schema import PageMeta, PageRecord
from .utils import guess_title_from_filename, sha1_text, sha1_text_compact

log = logging.getLogger(__name__)


def _build_section_index(doc: fitz.Document) -> Dict[int, str]:
    """
    TOC-based (section title) page -> section_title mapping.
    If page is between sections, use the nearest previous section.
    """
    toc = doc.get_toc(simple=True) or []  # list of [level, title, page]
    # page is 1-based
    section_by_page: Dict[int, str] = {}
    # last_title = None

    # fill page title based on each TOC entry
    # (simple strategy: same section title for current entry page to next entry page-1)
    spans = []
    for i, (_, title, page) in enumerate(toc):
        start = page
        end = toc[i + 1][2] - 1 if i + 1 < len(toc) else doc.page_count
        spans.append((start, end, title))

    for start, end, title in spans:
        for p in range(start, end + 1):
            section_by_page[p] = title

    return section_by_page


def load_pdf_to_pages(
    pdf_path: str | Path,
    *,
    doc_id: Optional[str] = None,
    default_url: Optional[str] = None,
    header_footer_patterns: Optional[Iterable[str]] = None,
    min_len: int = 30,
    preview: bool = True,
) -> List[PageRecord]:
    """
    Parse one PDF file and return a list of page records.
    - page text normalization
    - section title (if possible)
    - duplicate removal based on checksum
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    title = doc.metadata.get("title") or guess_title_from_filename(pdf_path)
    section_map = _build_section_index(doc)

    records: List[PageRecord] = []
    seen_checksums: set[str] = set()
    seen_compact: set[str] = set()

    _doc_id = doc_id or sha1_text(str(pdf_path.resolve()))
    source = pdf_path.name

    for i in range(doc.page_count):
        page_num = i + 1
        page = doc.load_page(i)

        # Extract raw text + simple layout reconstruction
        # (use .get_text("blocks") if needed)
        raw_text = page.get_text("text")

        # Normalization
        text = normalize_text(raw_text, header_footer_patterns=header_footer_patterns)

        # Skip too short or empty pages
        if len(text) < min_len:
            continue

        # checksum (based on normalized text)
        checksum = sha1_text(text)
        checksum2 = sha1_text_compact(text)
        if checksum in seen_checksums or checksum2 in seen_compact:
            # remove completely identical pages (scanned/repeated)
            continue
        seen_checksums.add(checksum)
        seen_compact.add(checksum2)

        meta = PageMeta(
            doc_id=_doc_id,
            source=source,
            title=title,
            page=page_num,
            section_title=section_map.get(page_num),
            url=default_url,  # usually not present but included in schema
            checksum=checksum,
            ingested_at=datetime.utcnow(),
            extra={},  # additional fields per document (if needed)
        )
        records.append(PageRecord(text=text, meta=meta))

    doc.close()

    # sample 500 chars preview
    if preview and records:
        sample = records[min(0, len(records) - 1)]
        log.info(
            "[loader] %s p%d preview: %s",
            source,
            sample.meta.page,
            (sample.text[:500] + ("…" if len(sample.text) > 500 else "")),
        )
        log.info("[loader] %s parsed pages: %d (unique)", source, len(records))
    return records


def load_many_pdfs(
    paths: list[str | Path],
    *,
    url_by_name: Optional[Dict[str, str]] = None,
    header_footer_patterns: Optional[Iterable[str]] = None,
) -> List[PageRecord]:
    """
    Traverse multiple PDFs and return the combined result.
    - If file name -> URL mapping exists, put it in meta.url
    """
    out: List[PageRecord] = []
    url_by_name = url_by_name or {}
    for p in paths:
        default_url = url_by_name.get(Path(p).name)
        out.extend(
            load_pdf_to_pages(
                p,
                default_url=default_url,
                header_footer_patterns=header_footer_patterns,
            )
        )
    return out
