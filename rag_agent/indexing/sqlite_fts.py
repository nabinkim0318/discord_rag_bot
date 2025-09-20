# rag_agent/indexing/sqlite_fts.py
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional

DDL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS chunks (
  doc_id     TEXT NOT NULL,
  chunk_id   INTEGER NOT NULL,
  chunk_uid  TEXT PRIMARY KEY,           -- f"{doc_id}#{chunk_id}"
  text       TEXT NOT NULL,
  title      TEXT,
  section    TEXT,
  page       INTEGER,
  source     TEXT,
  created_at REAL DEFAULT (strftime('%s','now'))
);

-- FTS5 virtual table. porter tokenizer(for English) used.
-- contentless mode is used, so we need to handle synchronization manually.
-- content=chunks + content_rowid is used here.
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
USING fts5(
  text,
  title,
  section,
  content='chunks',
  content_rowid='rowid',
  tokenize='porter'
);

-- content=chunks, triggers are not enabled by default.
-- INSERT/UPDATE/DELETE FTS synchronization is not enabled. Synchronize with triggers.
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts(rowid, text, title, section)
  VALUES (new.rowid, new.text, coalesce(new.title,''), coalesce(new.section,''));
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, text, title, section)
  VALUES('delete', old.rowid, old.text, coalesce(old.title,''),
  coalesce(old.section,''));
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, text, title, section)
  VALUES('delete', old.rowid, old.text, coalesce(old.title,''),
  coalesce(old.section,''));
  INSERT INTO chunks_fts(rowid, text, title, section)
  VALUES (new.rowid, new.text, coalesce(new.title,''), coalesce(new.section,''));
END;
"""


@contextmanager
def connect(db_path: str):
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON;")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_sqlite(db_path: str):
    with connect(db_path) as con:
        con.executescript(DDL)


def upsert_chunks(
    db_path: str,
    rows: Iterable[Dict[str, Any]],
    *,
    batch: int = 1000,
) -> int:
    """
    rows: [{doc_id, chunk_id, chunk_uid, text, title, section, page, source}, ...]
    If exists, UPDATE, otherwise INSERT.
    Triggers synchronize FTS5 automatically.
    """
    inserted_or_updated = 0
    with connect(db_path) as con:
        cur = con.cursor()
        cur.execute("BEGIN")
        for i, r in enumerate(rows, 1):
            cur.execute(
                """
        INSERT INTO chunks (doc_id, chunk_id, chunk_uid,
        text, title, section, page, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(chunk_uid) DO UPDATE SET
          text=excluded.text,
          title=excluded.title,
          section=excluded.section,
          page=excluded.page,
          source=excluded.source
        """,
                (
                    r["doc_id"],
                    int(r["chunk_id"]),
                    r["chunk_uid"],
                    r["text"],
                    r.get("title"),
                    r.get("section"),
                    r.get("page"),
                    r.get("source"),
                ),
            )
            if i % batch == 0:
                con.commit()
                cur.execute("BEGIN")
            inserted_or_updated += 1
        con.commit()
    # took = time.time() - t0
    return inserted_or_updated


def bm25_search(
    db_path: str,
    query: str,
    *,
    k: int = 5,
    where: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    BM25 search. chunks_fts → rowid to chunks Join.
    where: "source = '...'" additional filter condition (Optional)
    """
    sql = f"""
  SELECT c.doc_id, c.chunk_id, c.chunk_uid, c.text, c.title,
  c.section, c.page, c.source,
         bm25(chunks_fts) AS score
  FROM chunks_fts
  JOIN chunks c ON c.rowid = chunks_fts.rowid
  WHERE chunks_fts MATCH ?
  {"AND " + where if where else ""}
  ORDER BY score LIMIT ?;
  """
    with connect(db_path) as con:
        con.create_function(
            "bm25", 1, lambda x: x
        )  # FTS5 builtin function alias safety
        cur = con.execute(sql, (query, k))
        out = []
        for row in cur.fetchall():
            out.append(
                {
                    "doc_id": row[0],
                    "chunk_id": row[1],
                    "chunk_uid": row[2],
                    "text": row[3],
                    "title": row[4],
                    "section": row[5],
                    "page": row[6],
                    "source": row[7],
                    "bm25": row[8],
                }
            )
        return out


def fts_count(db_path: str) -> int:
    with connect(db_path) as con:
        cur = con.execute("SELECT COUNT(*) FROM chunks_fts;")
        return int(cur.fetchone()[0])


def table_count(db_path: str) -> int:
    with connect(db_path) as con:
        cur = con.execute("SELECT COUNT(*) FROM chunks;")
        return int(cur.fetchone()[0])
