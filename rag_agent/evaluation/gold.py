"""Load and validate retrieval-evaluation gold JSONL."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Sequence, Tuple

REQUIRED_FIELDS = ("qid", "question", "relevant_uids")


def load_gold_jsonl(path: str) -> List[Dict[str, Any]]:
    """
    Parse retrieval gold JSONL.

    Each non-empty line must be:
      {"qid": "...", "question": "...", "relevant_uids": ["doc_id#0"]}
    """
    records: List[Dict[str, Any]] = []
    seen_qids: set[str] = set()
    with open(path, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"gold line {line_no}: invalid JSON ({exc})") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"gold line {line_no}: expected a JSON object")
            missing = [key for key in REQUIRED_FIELDS if key not in obj]
            if missing:
                raise ValueError(f"gold line {line_no}: missing field(s) {missing}")
            qid = str(obj["qid"]).strip()
            question = str(obj["question"]).strip()
            relevant = obj["relevant_uids"]
            if not qid:
                raise ValueError(f"gold line {line_no}: empty qid")
            if qid in seen_qids:
                raise ValueError(f"gold line {line_no}: duplicate qid {qid!r}")
            if not question:
                raise ValueError(f"gold line {line_no}: empty question")
            if not isinstance(relevant, list) or not relevant:
                raise ValueError(
                    f"gold line {line_no}: relevant_uids must be a nonempty list"
                )
            cleaned = [str(uid).strip() for uid in relevant]
            if any(not uid for uid in cleaned):
                raise ValueError(
                    f"gold line {line_no}: relevant_uids contains an empty id"
                )
            seen_qids.add(qid)
            obj = dict(obj)
            obj["qid"] = qid
            obj["question"] = question
            obj["relevant_uids"] = cleaned
            records.append(obj)
    if not records:
        raise ValueError("No valid cases found in gold data")
    return records


def missing_uids_in_sqlite(sqlite_path: str, uids: Sequence[str]) -> List[str]:
    """Return gold UIDs that are absent from the chunks table."""
    missing: List[str] = []
    con = sqlite3.connect(sqlite_path)
    try:
        cur = con.cursor()
        for uid in uids:
            cur.execute("SELECT 1 FROM chunks WHERE chunk_uid=? LIMIT 1", (uid,))
            if cur.fetchone() is None:
                missing.append(uid)
    finally:
        con.close()
    return missing


def collect_relevant_uids(
    records: Sequence[Dict[str, Any]],
) -> List[str]:
    uids: List[str] = []
    seen: set[str] = set()
    for record in records:
        for uid in record.get("relevant_uids", []):
            if uid not in seen:
                seen.add(uid)
                uids.append(uid)
    return uids


def validate_gold_against_sqlite(
    gold_path: str, sqlite_path: str
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Load gold and confirm every relevant UID exists in sqlite.

    Returns (records, missing_uids).
    """
    records = load_gold_jsonl(gold_path)
    missing = missing_uids_in_sqlite(sqlite_path, collect_relevant_uids(records))
    return records, missing
