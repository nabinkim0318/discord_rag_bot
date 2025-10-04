# scripts/one_off_index.py
from __future__ import annotations

import argparse
from pathlib import Path

from rag_agent.indexing.hybrid_indexer import hybrid_index, sample_chunk_uids
from rag_agent.ingestion.chunker import chunk_text
from rag_agent.ingestion.loader import load_pdf_to_pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=str, help="PDF path")
    ap.add_argument("--text", type=str, help="Plain text path (fallback)")
    ap.add_argument("--sqlite", type=str, default="rag_kb.sqlite3")
    ap.add_argument("--doc-id", type=str, default="doc_bootcamp")
    ap.add_argument("--source", type=str, default="Bootcamp Docs")
    ap.add_argument("--no-weaviate", action="store_true", help="Disable Weaviate side")
    args = ap.parse_args()

    if args.pdf:
        pdf = Path(args.pdf)
        pages = load_pdf_to_pages(pdf)
        raw_text = "\n\n".join(p.text for p in pages)
        source = pdf.name
    elif args.text:
        p = Path(args.text)
        raw_text = p.read_text(encoding="utf-8")
        source = p.name
    else:
        raise SystemExit("Provide --pdf or --text")

    chunks = chunk_text(
        raw_text,
        max_chars=1000,
        overlap=200,
        section_path=None,
        base_meta={"ingested_at": "now", "checksum": "sha1:local"},
        doc_id=args.doc_id,
        source=source or args.source,
    )

    stats = hybrid_index(
        sqlite_path=args.sqlite,
        chunks=[c.to_dict() for c in chunks],
        embed_model=None,  # Use OpenAI if OPENAI_API_KEY available, otherwise pseudo
        weaviate_enabled=not args.no_weaviate,
    )
    print("[index] stats:", stats)

    uids = sample_chunk_uids([c.to_dict() for c in chunks], n=5)
    print("[index] sample chunk_uids:", uids)


if __name__ == "__main__":
    main()
