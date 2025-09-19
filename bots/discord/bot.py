# bots/discord/bot.py
# import asyncio
# from config import SETTINGS
import logging
import os
import re
import time
import uuid
from typing import Dict, Optional, Tuple

import httpx
import interactions
from httpx import Limits, Retry
from interactions import (
    ActionRow,
    Button,
    ButtonStyle,
    ComponentContext,
    MessageFlags,
    OptionType,
    SlashContext,
    component_callback,
    slash_command,
    slash_option,
)
from interactions.api.http import Forbidden
from metrics import RAG_FAILURES, RAG_LATENCY, RAG_TOTAL

logger = logging.getLogger("discord_bot")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# HTTP client configuration
retry = Retry(max_attempts=3, backoff_factor=0.5)
limits = Limits(max_keepalive_connections=20, max_connections=50)

BACKEND_BASE = os.environ.get("BACKEND_BASE", "http://api:8001")
METRICS_PATH = os.environ.get("METRICS_PATH", "/metrics")
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set. Check your .env")


async def call_backend_query(
    question: str, user_id: str, top_k: int = 5, channel_id: str | None = None
):
    headers = {
        "X-User-ID": user_id,
        "X-Channel-ID": channel_id or "",
        "X-Request-ID": str(uuid.uuid4()),
        "User-Agent": "discord-rag-bot/1.0",
    }
    async with httpx.AsyncClient(
        timeout=30.0, limits=limits, transport=httpx.AsyncHTTPTransport(retries=retry)
    ) as client:
        r = await client.post(
            f"{BACKEND_BASE}/api/query/",
            json={"query": question, "top_k": top_k, "user_id": user_id},
            headers=headers,
        )
        r.raise_for_status()
        return r.json()  # {answer, contexts, metadata, query_id}


async def call_backend_feedback(
    query_id: str, user_id: str, score: str, comment: Optional[str]
):
    headers = {
        "X-User-ID": user_id,
        "User-Agent": "discord-rag-bot/1.0",
    }
    async with httpx.AsyncClient(
        timeout=15.0, limits=limits, transport=httpx.AsyncHTTPTransport(retries=retry)
    ) as client:
        r = await client.post(
            f"{BACKEND_BASE}/api/v1/feedback/",
            json={"query_id": query_id, "feedback_type": score, "comment": comment},
            headers=headers,
        )
        r.raise_for_status()
        return r.json()


GUILD_ID = int(os.environ.get("DISCORD_TEST_GUILD_ID", "0"))
logger.info(f"Bot starting with guild ID: {GUILD_ID if GUILD_ID else 'None'}")

if GUILD_ID:
    BOT = interactions.Client(
        token=DISCORD_TOKEN,
        default_scope=[GUILD_ID],
    )
else:
    BOT = interactions.Client(token=DISCORD_TOKEN)
logger.info(f"Bot initialized with guild ID: {GUILD_ID if GUILD_ID else 'None'}")


def fb_buttons(query_id: str) -> ActionRow:
    up = Button(style=ButtonStyle.SUCCESS, label="👍", custom_id=f"fb:{query_id}:up")
    down = Button(style=ButtonStyle.DANGER, label="👎", custom_id=f"fb:{query_id}:down")
    return ActionRow(components=[up, down])


@slash_command(
    name="ping", description="bot alive check", scopes=[GUILD_ID] if GUILD_ID else None
)
async def ping(ctx: SlashContext):
    await ctx.send("pong!", flags=MessageFlags.EPHEMERAL)


@slash_command(
    name="ask",
    description="RAG chatbot ask question",
    scopes=[GUILD_ID] if GUILD_ID else None,
)
@slash_option(
    name="question",
    description="ask question",
    required=True,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="private",
    description="DM or channel (default: channel)",
    required=False,
    opt_type=OptionType.BOOLEAN,
)
async def ask(ctx: SlashContext, question: str, private: bool = False):
    await ctx.defer()

    start = time.perf_counter()

    try:
        payload = await call_backend_query(
            question,
            user_id=str(ctx.author.id),
            top_k=5,
            channel_id=str(ctx.channel_id),
        )
        answer = payload.get("answer", "[no answer]")
        query_id = payload.get("query_id") or str(uuid.uuid4())  # button fallback id
        latency = int((time.perf_counter() - start) * 1000)

        # DM or ephemeral fallback
        sent = None
        if private:
            try:
                user = await BOT.fetch_user(ctx.author.id)
                sent = await user.send(answer, components=fb_buttons(query_id))
            except Forbidden:
                sent = await ctx.send(
                    answer,
                    flags=MessageFlags.EPHEMERAL,
                    components=fb_buttons(query_id),
                )
            except Exception:
                sent = await ctx.send(
                    answer,
                    flags=MessageFlags.EPHEMERAL,
                    components=fb_buttons(query_id),
                )
        else:
            sent = await ctx.send(answer, components=fb_buttons(query_id))
            logger.info("Sent message to channel: {}", sent)

        # discord_message_id = getattr(sent, "id", None)
        RAG_TOTAL.inc()
        RAG_LATENCY.observe(latency / 1000.0)

    except httpx.HTTPError:
        RAG_TOTAL.inc()
        RAG_FAILURES.inc()
        # fail latency also aggregate (meaningful)
        RAG_LATENCY.observe((time.perf_counter() - start) / 1000.0)
        await ctx.send(
            "Backend is not responding. Please try again later.",
            flags=MessageFlags.EPHEMERAL,
        )

    except Exception:
        RAG_TOTAL.inc()
        RAG_FAILURES.inc()
        RAG_LATENCY.observe((time.perf_counter() - start) / 1000.0)
        await ctx.send(
            "Sorry, I can't answer your question right now. Please try again later.",
            flags=MessageFlags.EPHEMERAL,
        )


@component_callback("fb:", regex=True)
async def on_feedback_btn(ctx: ComponentContext):
    try:
        parts = ctx.custom_id.split(":")
        if len(parts) != 3:
            raise ValueError("invalid custom_id")
        _, query_id, score = parts
        if score not in ("up", "down"):
            raise ValueError("invalid score")

        await call_backend_feedback(
            query_id=query_id,
            user_id=str(ctx.author.id),
            score=score,
            comment=None,
        )
        await ctx.send("Thank you for your feedback!", flags=MessageFlags.EPHEMERAL)
    except ValueError as e:
        logger.warning("Invalid feedback button clicked: {}", e)
        await ctx.send(
            "Invalid feedback button. Please try again.", flags=MessageFlags.EPHEMERAL
        )
    except httpx.HTTPError:
        await ctx.send(
            "Backend is not responding. Please try again later.",
            flags=MessageFlags.EPHEMERAL,
        )
    except Exception:
        await ctx.send("Error processing feedback.", flags=MessageFlags.EPHEMERAL)


@slash_command(
    name="health", description="backend health", scopes=[GUILD_ID] if GUILD_ID else None
)
async def health(ctx: SlashContext):
    try:
        async with httpx.AsyncClient(
            timeout=5.0,
            limits=limits,
            transport=httpx.AsyncHTTPTransport(retries=retry),
        ) as client:
            r = await client.get(
                f"{BACKEND_BASE}/api/v1/health/",
                headers={"User-Agent": "discord-rag-bot/1.0"},
            )
            r.raise_for_status()
            data = r.json()
        await ctx.send(
            f"Backend: {data.get('status', 'unknown')}", flags=MessageFlags.EPHEMERAL
        )
    except Exception:
        await ctx.send("Backend health check failed.", flags=MessageFlags.EPHEMERAL)


PROM_LINE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)({.*})?\s+([0-9.eE+-]+)$")


def _labels_to_dict(label_str: str) -> Dict[str, str]:
    # label_str example: {endpoint="/api/query/", method="POST"}
    if not label_str:
        return {}
    label_str = label_str.strip()
    if label_str[0] == "{" and label_str[-1] == "}":
        label_str = label_str[1:-1]
    out = {}
    for kv in re.findall(r'(\w+)\s*=\s*"(.*?)"', label_str):
        out[kv[0]] = kv[1]
    return out


def parse_prometheus_text(text: str) -> Dict[str, Dict[Tuple, float]]:
    """
    Extract metric values by label set from Prometheus exposition format.
    return: { metric_name: { (('label','value'), ...): value } }
    """
    metrics: Dict[str, Dict[Tuple, float]] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        m = PROM_LINE.match(line.strip())
        if not m:
            continue
        name, label_str, val = m.groups()
        labels_dict = _labels_to_dict(label_str or "")
        key = tuple(sorted(labels_dict.items()))
        metrics.setdefault(name, {})[key] = float(val)
    return metrics


async def get_backend_text(url: str, timeout: float = 10.0) -> str:
    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        transport=httpx.AsyncHTTPTransport(retries=retry),
    ) as client:
        r = await client.get(url, headers={"User-Agent": "discord-rag-bot/1.0"})
        r.raise_for_status()
        return r.text


async def get_backend_json(url: str, timeout: float = 10.0) -> dict:
    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        transport=httpx.AsyncHTTPTransport(retries=retry),
    ) as client:
        r = await client.get(url, headers={"User-Agent": "discord-rag-bot/1.0"})
        r.raise_for_status()
        return r.json()


@slash_command(
    name="config",
    description="Show backend config & health",
    scopes=[GUILD_ID] if GUILD_ID else None,
)
async def config(ctx: SlashContext):
    await ctx.defer(flags=MessageFlags.EPHEMERAL)
    try:
        # health checks
        h_core = await get_backend_json(f"{BACKEND_BASE}/api/v1/health/")
        h_db = await get_backend_json(f"{BACKEND_BASE}/api/v1/health/db")
        h_llm = await get_backend_json(f"{BACKEND_BASE}/api/v1/health/llm")
        h_vec = await get_backend_json(f"{BACKEND_BASE}/api/v1/health/vector-store")

        # data sources (priority: ENV → None)
        sources_env = os.environ.get("DATA_SOURCES", "")
        sources = [s.strip() for s in sources_env.split(",") if s.strip()]
        sources_str = ", ".join(sources) if sources else "(not set)"

        lines = [
            f"**Backend**: `{BACKEND_BASE}`",
            f"**Core**: {h_core.get('status', 'unknown')}  "
            f"({h_core.get('duration', '-')}s)",
            f"**DB**: {h_db.get('status', 'unknown')}  "
            f"({h_db.get('duration', '-')}s)",
            f"**LLM**: {h_llm.get('status', 'unknown')}  "
            f"({h_llm.get('duration', '-')}s)",
            f"**Vector Store**: {h_vec.get('status', 'unknown')}  "
            f"({h_vec.get('duration', '-')}s)",
            f"**Data Sources**: {sources_str}",
        ]
        await ctx.send("\n".join(lines), flags=MessageFlags.EPHEMERAL)
    except httpx.HTTPError:
        await ctx.send(
            "Backend is not responding. Please try again later.",
            flags=MessageFlags.EPHEMERAL,
        )
    except Exception as e:
        logger.error(f"/config error: {e}")
        await ctx.send("Error fetching config.", flags=MessageFlags.EPHEMERAL)


@slash_command(
    name="metrics",
    description="Show RAG metrics summary",
    scopes=[GUILD_ID] if GUILD_ID else None,
)
async def metrics(ctx: SlashContext):
    await ctx.defer(flags=MessageFlags.EPHEMERAL)
    try:
        text = await get_backend_text(f"{BACKEND_BASE}{METRICS_PATH}", timeout=8.0)
        m = parse_prometheus_text(text)

        # Helpers to extract by label
        def by_label(name: str, want: Dict[str, str]) -> Dict[Tuple, float]:
            out = {}
            for labels, v in m.get(name, {}).items():
                lab = dict(labels)
                if all(lab.get(k) == v2 for k, v2 in want.items()):
                    out[labels] = v
            return out

        # rag_query_total by endpoint
        rag_total = m.get("rag_query_total", {})
        # rag_query_failures by endpoint
        rag_fail = m.get("rag_query_failures", {})
        # latency (sum/count) for each endpoint
        lat_sum = m.get("rag_query_latency_seconds_sum", {})
        lat_cnt = m.get("rag_query_latency_seconds_count", {})

        def label_str(labels: Tuple) -> str:
            d = dict(labels)
            return d.get("endpoint", "unknown")

        # summarize endpoints present in totals OR latency
        endpoints = set(
            label_str(label)
            for label in list(rag_total.keys())
            + list(lat_sum.keys())
            + list(lat_cnt.keys())
        )
        lines = ["**RAG Metrics**"]
        for ep in sorted(endpoints):
            # totals
            tot = sum(
                v for label, v in rag_total.items() if dict(label).get("endpoint") == ep
            )
            fail = sum(
                v for label, v in rag_fail.items() if dict(label).get("endpoint") == ep
            )
            # latency avg
            s = sum(
                v for label, v in lat_sum.items() if dict(label).get("endpoint") == ep
            )
            c = sum(
                v for label, v in lat_cnt.items() if dict(label).get("endpoint") == ep
            )
            avg_ms = (s / c * 1000.0) if c else 0.0
            lines.append(
                f"- `{ep}`: total={int(tot)} fail={int(fail)} "
                f"avg_latency={avg_ms:.0f}ms"
            )

        # feedback_total by type
        fb = m.get("feedback_total", {})
        up = sum(v for label, v in fb.items() if dict(label).get("type") == "up")
        down = sum(v for label, v in fb.items() if dict(label).get("type") == "down")
        lines.append(f"**Feedback**: 👍 {int(up)}  |  👎 {int(down)}")

        await ctx.send("\n".join(lines), flags=MessageFlags.EPHEMERAL)

    except httpx.HTTPError:
        await ctx.send(
            "Backend is not responding. Please try again later.",
            flags=MessageFlags.EPHEMERAL,
        )
    except Exception as e:
        logger.error(f"/metrics error: {e}")
        await ctx.send("Error fetching metrics.", flags=MessageFlags.EPHEMERAL)


if __name__ == "__main__":
    BOT.start()
