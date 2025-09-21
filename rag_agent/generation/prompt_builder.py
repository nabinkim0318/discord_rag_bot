# rag_agent/generation/prompt_builder.py
# Prompt engineering template collection
# → ✅ example: build_prompt(context, query) → str

import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from app.core.logging import logger
from app.core.metrics import record_prompt_version

# Load environment variables from root .env file
root_dir = Path(__file__).parent.parent.parent.parent
env_path = root_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class PromptBuilder:
    """prompt version management and template builder"""

    def __init__(self):
        self.prompt_versions = {
            "v1.0": self._build_v1_prompt,
            "v1.1": self._build_v1_1_prompt,
            "v2.0": self._build_v2_prompt,
        }
        self.current_version = "v1.1"

    def build_prompt(
        self, contexts: List[str], query: str, version: str = None, **kwargs
    ) -> Dict[str, Any]:
        """
        build prompt and return metadata

        Args:
            contexts: searched document contexts
            query: user question
            version: prompt version (None means use current version)
            **kwargs: additional parameters (temperature, max_tokens, etc.)

        Returns:
            Dict with 'prompt', 'version', 'metadata'
        """
        version = version or self.current_version
        prompt_func = self.prompt_versions.get(version, self._build_v1_1_prompt)

        record_prompt_version(version)

        prompt = prompt_func(contexts, query, **kwargs)

        return {
            "prompt": prompt,
            "version": version,
            "metadata": {
                "context_count": len(contexts),
                "query_length": len(query),
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            },
        }

    def _build_v1_prompt(self, contexts: List[str], query: str, **kwargs) -> str:
        """basic prompt v1.0"""
        logger.debug(
            f"Building prompt v1.0 with {len(contexts)} contexts and "
            f"{len(query)} query length"
        )
        context_text = "\n".join([f"- {ctx}" for ctx in contexts])
        return f"""Context Documents:
{context_text}

Question: {query}

Please provide a comprehensive answer based on the context documents above:"""

    def _build_v1_1_prompt(self, contexts: List[str], query: str, **kwargs) -> str:
        """improved prompt v1.1 - more specific instructions"""
        context_text = "\n".join([f"- {ctx}" for ctx in contexts])
        return f"""You are a helpful assistant. Use the following context documents to \
               answer the user's question accurately and comprehensively.

Context Documents:
{context_text}

Question: {query}

Instructions:
1. Answer based only on the provided context documents
2. If the context doesn't contain enough information, say so clearly
3. Be specific and cite relevant parts of the context
4. If you're uncertain, express that uncertainty

Answer:"""

    def _build_v2_prompt(self, contexts: List[str], query: str, **kwargs) -> str:
        """latest prompt v2.0 - structured response request"""
        context_text = "\n".join([f"- {ctx}" for ctx in contexts])
        return f"""# Task: Answer the user's question using provided context

## Context Documents:
{context_text}

## User Question:
{query}

## Response Guidelines:
- **Accuracy**: Base your answer strictly on the provided context
- **Completeness**: Address all aspects of the question
- **Clarity**: Use clear, concise language
- **Citations**: Reference specific parts of the context when relevant
- **Uncertainty**: Acknowledge limitations when context is insufficient

## Answer:"""

    def get_random_version(self) -> str:
        """select random version for A/B test"""
        return random.choice(list(self.prompt_versions.keys()))

    def get_version_metadata(self, version: str) -> Dict[str, Any]:
        """return version metadata"""
        return {
            "v1.0": {"description": "Basic prompt", "features": ["simple"]},
            "v1.1": {
                "description": "Enhanced with instructions",
                "features": ["instructions", "uncertainty"],
            },
            "v2.0": {
                "description": "Structured response",
                "features": ["structured", "citations", "guidelines"],
            },
        }.get(version, {})


# global instance
prompt_builder = PromptBuilder()


def build_prompt(
    contexts: List[str], query: str, version: str = None, **kwargs
) -> Dict[str, Any]:
    """convenience function"""
    return prompt_builder.build_prompt(contexts, query, version, **kwargs)
