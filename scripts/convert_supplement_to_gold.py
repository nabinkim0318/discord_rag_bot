#!/usr/bin/env python3
"""
Convert supplement dataset to evaluation gold format.
Generates relevant_uids from support information.
"""
import argparse
import json
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional


def normalize_source_name(source: str) -> str:
    """Normalize source name to match SQLite chunk_uid format."""
    # Remove file extension
    name = source.replace(".pdf", "").replace(".docx", "")

    # Replace spaces and special characters with underscores
    name = re.sub(r"[^\w\-&]", "_", name)

    # Clean up multiple underscores
    name = re.sub(r"_+", "_", name)

    return name.strip("_")


def find_chunk_uids_for_support(
    support: List[Dict], db_path: str, page_tolerance: int = 2
) -> List[str]:
    """
    Find chunk_uids in SQLite that match support information.

    Args:
        support: List of support dicts with 'source', 'page', 'snippet'
        db_path: Path to SQLite database
        page_tolerance: Allow ±N page difference

    Returns:
        List of matching chunk_uids
    """
    if not support:
        return []

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    found_uids = []

    try:
        for sup in support:
            source = sup.get("source", "")
            page = sup.get("page")

            if not source:
                continue

            # Normalize source name
            norm_source = normalize_source_name(source)

            # Search for matching chunks
            if page is not None:
                # Try exact page match first
                cur.execute(
                    """
                    SELECT chunk_uid FROM chunks
                    WHERE source LIKE ? AND page = ?
                """,
                    (f"%{norm_source}%", page),
                )
                results = cur.fetchall()

                # If no exact match, try page range
                if not results and page_tolerance > 0:
                    cur.execute(
                        """
                        SELECT chunk_uid FROM chunks
                        WHERE source LIKE ? AND page BETWEEN ? AND ?
                    """,
                        (
                            f"%{norm_source}%",
                            max(1, page - page_tolerance),
                            page + page_tolerance,
                        ),
                    )
                    results = cur.fetchall()
            else:
                # No page info, just match source
                cur.execute(
                    """
                    SELECT chunk_uid FROM chunks
                    WHERE source LIKE ?
                """,
                    (f"%{norm_source}%",),
                )
                results = cur.fetchall()

            # Extract chunk_uids
            for (chunk_uid,) in results:
                if chunk_uid not in found_uids:
                    found_uids.append(chunk_uid)

    finally:
        conn.close()

    return found_uids


def convert_case_to_gold(
    case: Dict[str, Any], db_path: str
) -> Optional[Dict[str, Any]]:
    """Convert a single case to gold format."""
    # Extract basic info
    qid = case.get("id", case.get("qid", ""))
    question = case.get("question", "")
    answer = case.get("answer", "")
    support = case.get("support", [])

    if not qid or not question:
        return None

    # Find relevant chunk_uids
    relevant_uids = find_chunk_uids_for_support(support, db_path)

    if not relevant_uids:
        print(f"Warning: No chunk_uids found for case {qid}")
        # Fallback: try to find any chunks from the source
        for sup in support:
            source = sup.get("source", "")
            if source:
                norm_source = normalize_source_name(source)
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT chunk_uid FROM chunks
                    WHERE source LIKE ? LIMIT 3
                """,
                    (f"%{norm_source}%",),
                )
                results = cur.fetchall()
                conn.close()

                for (chunk_uid,) in results:
                    if chunk_uid not in relevant_uids:
                        relevant_uids.append(chunk_uid)
                break

    # Create gold case
    gold_case = {
        "qid": qid,
        "question": question,
        "relevant_uids": relevant_uids,
        "answer": answer,
        "support": support,
        "intent": case.get("intent", ""),
        "difficulty": case.get("difficulty", ""),
        "answer_type": case.get("answer_type", ""),
        "unanswerable": case.get("unanswerable", False),
        "reasoning_note": case.get("reasoning_note", ""),
        "canonical_terms": case.get("canonical_terms", []),
        "paraphrases": case.get("paraphrases", []),
        "constraints": case.get("constraints", []),
        "expected_span": case.get("expected_span", answer),
    }

    return gold_case


def main():
    parser = argparse.ArgumentParser(
        description="Convert supplement dataset to gold format"
    )
    parser.add_argument("--sqlite", required=True, help="Path to SQLite database")
    parser.add_argument("--in-jsonl", required=True, help="Input JSONL file")
    parser.add_argument("--out-jsonl", required=True, help="Output JSONL file")
    parser.add_argument(
        "--vector-backup", action="store_true", help="Enable vector search backup"
    )
    parser.add_argument(
        "--page-tolerance", type=int, default=2, help="Page tolerance for matching"
    )

    args = parser.parse_args()

    if not os.path.exists(args.sqlite):
        print(f"Error: SQLite database not found: {args.sqlite}")
        return 1

    if not os.path.exists(args.in_jsonl):
        print(f"Error: Input file not found: {args.in_jsonl}")
        return 1

    print(f"Converting {args.in_jsonl} to {args.out_jsonl}")
    print(f"Using database: {args.sqlite}")

    converted_cases = []
    skipped_cases = []

    with open(args.in_jsonl, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("이게"):
                continue

            try:
                case = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON at line {i}: {e}")
                continue

            gold_case = convert_case_to_gold(case, args.sqlite)
            if gold_case:
                converted_cases.append(gold_case)
            else:
                skipped_cases.append(case.get("id", f"line_{i}"))

    # Write converted cases
    with open(args.out_jsonl, "w", encoding="utf-8") as f:
        for case in converted_cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    print(f"✅ Converted {len(converted_cases)} cases")
    if skipped_cases:
        print(f"⚠️ Skipped {len(skipped_cases)} cases: {skipped_cases[:5]}")

    # Show sample
    if converted_cases:
        print("\n📋 Sample converted cases:")
        for i, case in enumerate(converted_cases[:3]):
            print(f"{i+1}. {case['qid']}: {case['question'][:50]}...")
            print(f"   Relevant UIDs: {case['relevant_uids']}")

    return 0


if __name__ == "__main__":
    exit(main())
