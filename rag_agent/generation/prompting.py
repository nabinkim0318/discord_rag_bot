# rag_agent/generation/prompting.py
from __future__ import annotations

from typing import Any, Dict

from rag_agent.generation.prompt_builder import build_prompt


def build_rag_prompt(
    context_block: str, query: str, version: str = "v1.1"
) -> Dict[str, Any]:
    """
    instead of putting the context text array into prompt_builder,
    if you want to put a single merged block, pass it
    in the form of contexts=[context_block].
    If you want to put a single merged block, pass it
    in the form of contexts=[context_block].
    """
    data = build_prompt([context_block], query, version=version)
    # build_prompt internally constructs in the form of "Context Documents:\n- <ctx>",
    # so if you pass it as a single item, it will be neatly added.
    return data
