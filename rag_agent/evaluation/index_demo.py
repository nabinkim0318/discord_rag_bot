"""Build a sqlite/FTS index from the committed demo corpus."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from rag_agent.indexing.hybrid_indexer import hybrid_index
from rag_agent.indexing.sqlite_fts import table_count
from rag_agent.ingestion.chunker import chunk_text

DEMO_ROOT = Path(__file__).resolve().parents[1] / "demo"
CORPUS_DIR = DEMO_ROOT / "corpus"
DEFAULT_SQLITE = Path(__file__).resolve().parents[1] / ".demo" / "demo_kb.sqlite3"
CHUNK_MAX_CHARS = 1000
CHUNK_OVERLAP = 200


def _corpus_files(corpus_dir: Path) -> List[Path]:
    files = sorted(p for p in corpus_dir.glob("*.txt") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No .txt files in demo corpus: {corpus_dir}")
    return files


def _remove_sqlite(path: Path) -> None:
    if path.exists():
        path.unlink()
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists():
            sidecar.unlink()


def chunk_corpus(corpus_dir: Path | None = None) -> List[Dict[str, Any]]:
    """Chunk each committed demo text file with the production chunker."""
    corpus_dir = Path(corpus_dir or CORPUS_DIR)
    chunks: List[Dict[str, Any]] = []
    for path in _corpus_files(corpus_dir):
        text = path.read_text(encoding="utf-8")
        doc_id = path.stem
        produced = chunk_text(
            text,
            max_chars=CHUNK_MAX_CHARS,
            overlap=CHUNK_OVERLAP,
            section_path=None,
            base_meta={"ingested_at": "demo", "checksum": f"demo:{doc_id}"},
            doc_id=doc_id,
            source=path.name,
        )
        if not produced:
            raise ValueError(f"Chunker produced no chunks for {path.name}")
        chunks.extend(c.to_dict() for c in produced)
    return chunks


def expected_uids(chunks: List[Dict[str, Any]]) -> List[str]:
    uids = []
    for chunk in chunks:
        meta = chunk.get("meta") or {}
        doc_id = meta.get("doc_id") or "unknown_doc"
        chunk_id = meta.get("chunk_id")
        if chunk_id is None:
            raise ValueError("chunk is missing meta.chunk_id")
        uids.append(f"{doc_id}#{int(chunk_id)}")
    return uids


def build_demo_index(
    sqlite_path: str | Path | None = None,
    *,
    corpus_dir: Path | None = None,
    recreate: bool = True,
) -> Dict[str, Any]:
    """
    Recreate a sqlite-only demo index from the committed corpus.

    Does not call Weaviate, embeddings, or LLM APIs.
    """
    sqlite_path = Path(sqlite_path or DEFAULT_SQLITE)
    corpus_dir = Path(corpus_dir or CORPUS_DIR)
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    if recreate:
        _remove_sqlite(sqlite_path)

    files = _corpus_files(corpus_dir)
    chunks = chunk_corpus(corpus_dir)
    uids = expected_uids(chunks)

    stats = hybrid_index(
        sqlite_path=str(sqlite_path),
        chunks=chunks,
        embed_model=None,
        weaviate_enabled=False,
    )
    n_chunks = table_count(str(sqlite_path))
    if n_chunks != len(chunks):
        raise RuntimeError(
            f"Demo index chunk count {n_chunks} != produced {len(chunks)}"
        )
    result = {
        "sqlite_path": str(sqlite_path),
        "n_docs": len(files),
        "n_chunks": n_chunks,
        "uids": uids,
        "index_stats": stats,
    }
    print(
        f"[demo-index] docs={result['n_docs']} chunks={result['n_chunks']} "
        f"sqlite={sqlite_path}"
    )
    print("[demo-index] uids: " + ", ".join(uids))
    return result


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the offline demo sqlite/FTS index from committed corpus."
    )
    parser.add_argument(
        "--sqlite",
        default=str(DEFAULT_SQLITE),
        help="generated sqlite path (not tracked source)",
    )
    parser.add_argument(
        "--corpus",
        default=str(CORPUS_DIR),
        help="directory of UTF-8 .txt files",
    )
    args = parser.parse_args(argv)
    try:
        build_demo_index(args.sqlite, corpus_dir=Path(args.corpus), recreate=True)
    except Exception as exc:
        print(f"[demo-index] FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
