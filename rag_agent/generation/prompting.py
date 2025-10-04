# rag_agent/generation/prompting.py
from __future__ import annotations

from typing import Any, Dict

from rag_agent.generation.prompt_builder import build_prompt


def build_rag_prompt(
    context_block: str, query: str, version: str = "v1.1"
) -> Dict[str, Any]:
    # if v2.1, insert JSON schema instruction here + llm_client(force_json=True)
    return build_prompt([context_block], query, version=version)
