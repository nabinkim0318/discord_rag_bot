# rag_agent/generation/llm_client.py
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Generator, Optional, Tuple

from dotenv import load_dotenv

# add project root to Python path
project_root = Path(__file__).parent.parent
print(project_root)
sys.path.insert(0, str(project_root))

# load environment variables from project root
print(project_root / ".env")
load_dotenv(project_root / ".env")

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]  # repo root
load_dotenv(ROOT / ".env")  # ✅ root .env only


# Try OpenAI SDK 1.x
try:
    from openai import AzureOpenAI, OpenAI  # type: ignore
except Exception:  # SDK not installed, module still loads
    OpenAI = None
    AzureOpenAI = None


# -------------------------------
# Small retry decorator (backoff+jitter)
# -------------------------------
def _retry(max_attempts: int = 3, base_delay: float = 0.5, max_delay: float = 8.0):
    def deco(fn):
        def wrapper(*args, **kwargs):
            attempt = 0
            delay = base_delay
            last_err = None
            while attempt < max_attempts:
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    attempt += 1
                    if attempt >= max_attempts:
                        break
                    sleep_for = min(max_delay, delay)
                    logger.warning(
                        f"[llm_client] attempt {attempt}/{max_attempts} failed: {e}. "
                        f"retrying in {sleep_for:.2f}s"
                    )
                    time.sleep(sleep_for)
                    delay *= 2.0
            raise last_err  # re-raise last error

        return wrapper

    return deco


# -------------------------------
# Client factory
# -------------------------------
def _make_client() -> Tuple[object, Tuple[str, str]]:
    """
    Return: (client, (kind, model_or_deployment))
      - kind: "azure" | "openai"
    Priority: Azure OpenAI → OpenAI/compatible
    """
    # Azure OpenAI priority
    if (
        AzureOpenAI
        and os.getenv("AZURE_OPENAI_API_KEY")
        and os.getenv("AZURE_OPENAI_ENDPOINT")
    ):
        dep = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not dep:
            raise RuntimeError("AZURE_OPENAI_DEPLOYMENT is required.")
        cli = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        )
        return cli, ("azure", dep)
    if OpenAI and os.getenv("OPENAI_API_KEY"):
        cli = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
        mdl = os.getenv("LLM_MODEL", "gpt-4o-mini")
        return cli, ("openai", mdl)
    raise RuntimeError("No LLM credentials. Set Azure or OpenAI envs.")


# -------------------------------
# Main call function
# -------------------------------
@_retry()
def llm_generate(
    prompt: str,
    *,
    system_prompt: Optional[str] = "You are a helpful assistant.",
    max_tokens: Optional[int] = None,
    temperature: float = 0.2,
    stream: bool = False,
    force_json: bool = False,  # ✅ v2.1 대비
) -> str | Generator[str, None, None]:

    client, (kind, model) = _make_client()
    max_tokens = max_tokens or int(os.getenv("LLM_MAX_TOKENS", "600"))

    msgs = [{"role": "system", "content": system_prompt}] if system_prompt else []
    msgs.append({"role": "user", "content": prompt})

    kwargs = dict(
        model=model,
        messages=msgs,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=stream,
    )
    # OpenAI 일부 모델: response_format 지원
    if force_json and kind == "openai":
        kwargs["response_format"] = {"type": "json_object"}

    if stream:
        resp = client.chat.completions.create(**kwargs)

        def gen():
            for ch in resp:
                delta = getattr(ch.choices[0].delta, "content", "") or ""
                if delta:
                    yield delta

        return gen()
    else:
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
