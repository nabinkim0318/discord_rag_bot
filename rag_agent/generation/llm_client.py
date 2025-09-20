# rag_agent/generation/llm_client.py
from __future__ import annotations

from typing import Generator, Optional

from app.core.config import settings
from app.core.logging import logger
from app.core.retry import retry_openai

try:
    # OpenAI SDK 1.x
    from openai import AzureOpenAI, OpenAI
except Exception:
    OpenAI = None
    AzureOpenAI = None


def _make_client():
    """
    OpenAI / Azure OpenAI / OpenAI-compatible(DeepSeek 등) 클라이언트 구성
    """
    if AzureOpenAI and settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
        return AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        ), ("azure", settings.AZURE_OPENAI_DEPLOYMENT or settings.OPENAI_MODEL)

    if OpenAI and settings.OPENAI_API_KEY:
        base_url = settings.OPENAI_BASE_URL or None  # DeepSeek 등 호환 엔드포인트
        return OpenAI(api_key=settings.OPENAI_API_KEY, base_url=base_url), (
            "openai",
            settings.OPENAI_MODEL,
        )

    raise RuntimeError(
        "No LLM credentials found. Set OPENAI_API_KEY or Azure OpenAI vars."
    )


@retry_openai(max_attempts=3)
def llm_generate(
    prompt: str,
    *,
    system_prompt: Optional[str] = "You are a helpful assistant.",
    max_tokens: Optional[int] = None,
    temperature: float = 0.2,
    stream: bool = False,
) -> str | Generator[str, None, None]:
    """
    Chat Completions wrapper. 비스트리밍 시 최종 텍스트, 스트리밍 시 토큰 generator 반환.
    """
    client, (kind, model_or_deploy) = _make_client()
    max_tokens = max_tokens or settings.GENERATION_MAX_TOKENS

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    logger.debug(
        f"Calling LLM [{kind}:{model_or_deploy}] tokens={max_tokens}, stream={stream}"
    )

    if kind == "azure":
        # Azure: model=deployment name
        if stream:
            resp = client.chat.completions.create(
                model=model_or_deploy,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            def gen():
                for chunk in resp:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield delta

            return gen()
        else:
            resp = client.chat.completions.create(
                model=model_or_deploy,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
            )
            return resp.choices[0].message.content or ""

    # OpenAI / compatible
    if stream:
        resp = client.chat.completions.create(
            model=model_or_deploy,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        def gen():
            for chunk in resp:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta

        return gen()
    else:
        resp = client.chat.completions.create(
            model=model_or_deploy,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
        )
        return resp.choices[0].message.content or ""
