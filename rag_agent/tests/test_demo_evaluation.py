"""Regression tests for the public offline retrieval-evaluation demo."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from rag_agent.evaluation.cli_eval import build_parser, config_from_args, main
from rag_agent.evaluation.evaluator import EvaluationConfig, run_evaluation
from rag_agent.evaluation.gold import load_gold_jsonl, validate_gold_against_sqlite
from rag_agent.evaluation.index_demo import (
    build_demo_index,
    chunk_corpus,
    expected_uids,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RAG_ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = RAG_ROOT / "demo" / "gold.jsonl"
CORPUS_DIR = RAG_ROOT / "demo" / "corpus"
MAKEFILE = REPO_ROOT / "Makefile"
GITIGNORE = REPO_ROOT / ".gitignore"

EXPECTED_UIDS = {
    "alpine_gentian#0",
    "harbor_lantern#0",
    "honey_super#0",
    "kiln_firing#0",
    "rye_levain#0",
    "transit_token#0",
}


def _offline_config(sqlite_path: Path, out_dir: Path, **overrides) -> EvaluationConfig:
    kwargs = dict(
        sqlite_path=str(sqlite_path),
        out_dir=str(out_dir),
        retrieval_mode="bm25",
        enable_vector=False,
        require_vector=False,
        use_rerank=False,
        enforce_latency=False,
        ndcg_threshold=0.5,
        hit_rate_threshold=0.8,
        k_final=8,
        k_bm25=20,
        k_vec=20,
    )
    kwargs.update(overrides)
    return EvaluationConfig(**kwargs)


def _build_demo_sqlite(tmp_path: Path) -> Path:
    sqlite_path = tmp_path / "demo_kb.sqlite3"
    result = build_demo_index(sqlite_path, corpus_dir=CORPUS_DIR, recreate=True)
    assert result["n_docs"] == 6
    assert result["n_chunks"] >= 6
    return sqlite_path


def _makefile_target(name: str) -> str:
    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(
        rf"^{re.escape(name)}:.*\n((?:[ \t].*\n)*)",
        text,
        flags=re.M,
    )
    assert match, f"Make target {name} not found"
    return match.group(0)


def test_committed_demo_gold_parses_as_jsonl_schema():
    records = load_gold_jsonl(str(GOLD_PATH))
    assert len(records) >= 6
    qids = [row["qid"] for row in records]
    assert len(qids) == len(set(qids))
    for row in records:
        assert row["qid"]
        assert row["question"]
        assert isinstance(row["relevant_uids"], list) and row["relevant_uids"]
        for uid in row["relevant_uids"]:
            assert re.fullmatch(r"[A-Za-z0-9_]+#\d+", uid), uid


def test_demo_corpus_builds_sqlite_and_expected_uids(tmp_path):
    sqlite_path = _build_demo_sqlite(tmp_path)
    chunks = chunk_corpus(CORPUS_DIR)
    uids = expected_uids(chunks)
    assert EXPECTED_UIDS.issubset(set(uids))
    records, missing = validate_gold_against_sqlite(str(GOLD_PATH), str(sqlite_path))
    assert records
    assert missing == []


def test_evaluator_rejects_malformed_and_empty_gold(tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="No valid cases"):
        load_gold_jsonl(str(empty))
    with pytest.raises(ValueError, match="No valid cases"):
        run_evaluation(
            str(empty),
            _offline_config(tmp_path / "none.sqlite3", tmp_path / "out"),
        )

    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        '{"qid": "q1", "question": "ok", "relevant_uids": ["a#0"]}\n'
        '{"qid": "q1", "question": "dup", "relevant_uids": ["a#0"]}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate qid"):
        load_gold_jsonl(str(bad))

    empty_q = tmp_path / "empty_q.jsonl"
    empty_q.write_text(
        '{"qid": "q1", "question": "   ", "relevant_uids": ["a#0"]}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="empty question"):
        load_gold_jsonl(str(empty_q))

    empty_uids = tmp_path / "empty_uids.jsonl"
    empty_uids.write_text(
        '{"qid": "q1", "question": "ok", "relevant_uids": []}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="nonempty list"):
        load_gold_jsonl(str(empty_uids))

    not_json = tmp_path / "not_json.jsonl"
    not_json.write_text("{not json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_gold_jsonl(str(not_json))


def test_offline_mode_never_invokes_vector_or_weaviate(tmp_path, monkeypatch):
    sqlite_path = _build_demo_sqlite(tmp_path)

    def _boom(*_args, **_kwargs):
        raise AssertionError("vector/weaviate path must not run in offline mode")

    fake_vector = types.ModuleType("rag_agent.retrieval.vector")
    fake_vector.vector_search = _boom
    fake_weaviate = types.ModuleType("rag_agent.indexing.weaviate_index")
    fake_weaviate.fetch_by_chunk_uid = _boom
    fake_weaviate.ensure_schema = _boom
    fake_embed = types.ModuleType("rag_agent.indexing.embeddings")
    fake_embed.embed_texts = _boom

    monkeypatch.setitem(sys.modules, "rag_agent.retrieval.vector", fake_vector)
    monkeypatch.setitem(sys.modules, "rag_agent.indexing.weaviate_index", fake_weaviate)
    monkeypatch.setitem(sys.modules, "rag_agent.indexing.embeddings", fake_embed)

    per_case, summary = run_evaluation(
        str(GOLD_PATH), _offline_config(sqlite_path, tmp_path / "out")
    )
    assert per_case
    assert summary.total == len(per_case)
    assert summary.retrieval_mode == "bm25"


def test_offline_mode_does_not_require_api_key_or_dotenv(tmp_path, monkeypatch):
    sqlite_path = _build_demo_sqlite(tmp_path)
    for key in (
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "WEAVIATE_URL",
        "WEAVIATE_API_KEY",
        "WEAVIATE_HOST",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    per_case, summary = run_evaluation(
        str(GOLD_PATH),
        _offline_config(sqlite_path, tmp_path / "out"),
    )
    assert per_case
    assert 0.0 <= summary.hit_rate <= 1.0
    assert 0.0 <= summary.ndcg_at_k_mean <= 1.0
    assert 0.0 <= summary.mrr_at_k_mean <= 1.0
    assert 0.0 <= summary.p_at_k_mean <= 1.0
    assert 0.0 <= summary.r_at_k_mean <= 1.0
    assert 0.0 <= summary.map_at_k_mean <= 1.0


def test_make_eval_rag_demo_uses_valid_cli_only():
    makefile = MAKEFILE.read_text(encoding="utf-8")
    assert "--input" not in makefile
    assert "--prompt-version" not in makefile
    assert re.search(r"^eval-rag-all:", makefile, flags=re.M) is None
    assert re.search(r"^eval-rag:", makefile, flags=re.M) is None
    assert "poetry run python" in makefile
    assert ".venv/bin/python" not in makefile
    assert "-u PYTHONHOME" in makefile
    eval_python_line = next(
        line
        for line in makefile.splitlines()
        if "RAG_EVAL_PYTHON" in line and "poetry" in line
    )
    assert "poetry run python" in eval_python_line

    parser = build_parser()
    known = {opt for action in parser._actions for opt in action.option_strings}

    demo_block = _makefile_target("eval-rag-demo")
    flags = re.findall(r"--[a-z0-9-]+", demo_block)
    for flag in flags:
        assert flag in known, f"Make demo target uses unknown flag {flag}"

    assert "--gold" in demo_block
    assert "--mode" in demo_block
    assert "bm25" in demo_block
    assert "--no-latency-gate" in demo_block


def test_retained_cli_options_propagate_to_retrieval_config_and_call(tmp_path):
    parser = build_parser()
    option_names = {opt for action in parser._actions for opt in action.option_strings}
    assert "--rerank-model" in option_names
    assert "--use-rerank" in option_names
    assert "--bm25-weight" in option_names
    assert "--vec-weight" in option_names
    assert "--offline" in option_names
    assert "--mode" in option_names
    assert "--mmr" not in option_names
    assert "--input" not in option_names
    assert "--prompt-version" not in option_names

    args = parser.parse_args(
        [
            "--gold",
            "demo/gold.jsonl",
            "--sqlite",
            "tmp.sqlite3",
            "--offline",
            "--rerank-model",
            "unit-test-rerank",
            "--use-rerank",
            "true",
            "--bm25-weight",
            "0.91",
            "--vec-weight",
            "0.09",
            "--k-final",
            "5",
            "--k-bm25",
            "11",
            "--k-vec",
            "13",
            "--preselect-topn",
            "7",
            "--per-doc-cap",
            "2",
            "--rrf-c",
            "21",
            "--no-latency-gate",
        ]
    )
    cfg = config_from_args(args)
    assert cfg.retrieval_mode == "bm25"
    assert cfg.enable_vector is False
    assert cfg.require_vector is False
    assert cfg.rerank_model == "unit-test-rerank"
    assert cfg.use_rerank is True
    assert cfg.bm25_weight == 0.91
    assert cfg.vec_weight == 0.09
    assert cfg.k_final == 5
    assert cfg.k_bm25 == 11
    assert cfg.k_vec == 13
    assert cfg.preselect_topn == 7
    assert cfg.per_doc_cap == 2
    assert cfg.rrf_c == 21
    assert cfg.enforce_latency is False

    gold = tmp_path / "gold.jsonl"
    gold.write_text(
        json.dumps(
            {
                "qid": "q1",
                "question": "harbor lantern whale oil",
                "relevant_uids": ["harbor_lantern#0"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cfg.out_dir = str(tmp_path / "out")
    with patch(
        "rag_agent.evaluation.evaluator.search_hybrid", return_value=[]
    ) as mocked:
        run_evaluation(str(gold), cfg)

    kwargs = mocked.call_args.kwargs
    assert kwargs["enable_vector"] is False
    assert kwargs["require_vector"] is False
    assert kwargs["use_rerank"] is True
    assert kwargs["rerank_model"] == "unit-test-rerank"
    assert kwargs["bm25_weight"] == 0.91
    assert kwargs["vec_weight"] == 0.09
    assert kwargs["k_bm25"] == 11
    assert kwargs["k_vec"] == 13
    assert kwargs["top_k_final"] == 5
    assert kwargs["preselect_topn"] == 7
    assert kwargs["per_doc_cap"] == 2
    assert kwargs["rrf_c"] == 21
    assert kwargs["db_path"] == "tmp.sqlite3"


def test_demo_evaluation_nonempty_and_deterministic(tmp_path):
    sqlite_path = _build_demo_sqlite(tmp_path)
    cfg_a = _offline_config(sqlite_path, tmp_path / "out-a")
    cfg_b = _offline_config(sqlite_path, tmp_path / "out-b")
    cases_a, summary_a = run_evaluation(str(GOLD_PATH), cfg_a)
    cases_b, summary_b = run_evaluation(str(GOLD_PATH), cfg_b)

    assert len(cases_a) >= 6
    assert summary_a.total == len(cases_a)
    assert summary_a.hit_rate >= 0.8
    assert summary_a.ndcg_at_k_mean >= 0.5
    assert summary_a.passed is True

    ranking_a = [(c.qid, c.ranked_uids, c.relevant_uids) for c in cases_a]
    ranking_b = [(c.qid, c.ranked_uids, c.relevant_uids) for c in cases_b]
    assert ranking_a == ranking_b

    metric_keys = (
        "total",
        "p_at_k_mean",
        "r_at_k_mean",
        "ndcg_at_k_mean",
        "mrr_at_k_mean",
        "map_at_k_mean",
        "hit_rate",
        "passed",
        "failure_reason",
        "retrieval_mode",
    )
    for key in metric_keys:
        assert getattr(summary_a, key) == getattr(summary_b, key)


def test_missing_gold_uid_fail_fast(tmp_path):
    sqlite_path = _build_demo_sqlite(tmp_path)
    gold = tmp_path / "missing.jsonl"
    gold.write_text(
        json.dumps(
            {
                "qid": "q_missing",
                "question": "Northhaven harbor lantern whale oil",
                "relevant_uids": ["does_not_exist#0"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    records, missing = validate_gold_against_sqlite(str(gold), str(sqlite_path))
    assert records
    assert "does_not_exist#0" in missing

    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--gold",
                str(gold),
                "--sqlite",
                str(sqlite_path),
                "--mode",
                "bm25",
                "--out-dir",
                str(tmp_path / "out"),
                "--no-latency-gate",
                "--fail-fast-uid",
                "true",
                "--use-rerank",
                "false",
            ]
        )
    assert exc.value.code == 1


def test_generated_outputs_are_gitignored_and_untracked():
    ignore_text = GITIGNORE.read_text(encoding="utf-8")
    assert "rag_agent/.demo/" in ignore_text
    assert "rag_agent/evaluation_results/" in ignore_text

    git_probe = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if git_probe.returncode != 0:
        pytest.skip("git metadata is required for check-ignore / ls-files")

    ignored_paths = [
        "rag_agent/.demo/demo_kb.sqlite3",
        "rag_agent/.demo/evaluation_results/summary.json",
        "rag_agent/evaluation_results/summary.json",
    ]
    for rel_path in ignored_paths:
        check = subprocess.run(
            ["git", "check-ignore", "-q", rel_path],
            cwd=REPO_ROOT,
        )
        assert check.returncode == 0, rel_path

    tracked = subprocess.check_output(
        ["git", "ls-files", "rag_agent/.demo", "rag_agent/evaluation_results"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    assert tracked == ""


def test_hybrid_mode_does_not_silently_fallback_to_bm25(tmp_path):
    sqlite_path = _build_demo_sqlite(tmp_path)
    cfg = _offline_config(
        sqlite_path,
        tmp_path / "out",
        retrieval_mode="hybrid",
        enable_vector=True,
        require_vector=True,
    )

    def _fail(*_args, **_kwargs):
        raise RuntimeError("weaviate unavailable")

    fake_vector = types.ModuleType("rag_agent.retrieval.vector")
    fake_vector.vector_search = _fail
    with patch.dict(sys.modules, {"rag_agent.retrieval.vector": fake_vector}):
        with pytest.raises(RuntimeError, match="weaviate unavailable"):
            run_evaluation(str(GOLD_PATH), cfg)
