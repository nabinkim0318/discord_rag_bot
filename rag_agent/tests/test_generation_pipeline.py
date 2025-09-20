# rag_agent/tests/test_generation_pipeline.py
from rag_agent.generation.generation_pipeline import generate_answer


def test_generate_answer_smoke():
    out, chosen, meta = generate_answer(
        "What are office hours?", k_final=3, reranker=None, stream=False
    )
    assert isinstance(out, str)
    assert isinstance(chosen, list)
    assert "packing" in meta
