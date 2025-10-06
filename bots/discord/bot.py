# bots/discord/bot.py
# import asyncio
# from config import SETTINGS
import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx
import interactions
from dotenv import load_dotenv
from httpx import Limits
from interactions import (  # events,  # optional for future global listeners
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

# from interactions.api.http import Forbidden  # Commented out due to version compatibility
# from metrics import RAG_FAILURES, RAG_LATENCY, RAG_TOTAL  # Commented out due to missing module

# from rag_agent.core.logging import logger  # Commented out due to missing module

# add project root to Python path
project_root = Path(__file__).parent.parent
# logger.info(project_root)  # Commented out due to missing logger
sys.path.insert(0, str(project_root))

# load environment variables from project root
# logger.info(project_root / ".env")  # Commented out due to missing logger
load_dotenv(project_root / ".env")

logger = logging.getLogger("discord_bot")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# Global mappings for interaction context
# message ID → backend query_id
MESSAGE_QID: Dict[int, str] = {}
# message ID → original question text
MESSAGE_QUESTION: Dict[int, str] = {}

# HTTP client configuration
# retry = Retry(max_attempts=3, backoff_factor=0.5)  # Commented out due to httpx version compatibility
limits = Limits(max_keepalive_connections=20, max_connections=50)

BACKEND_BASE = os.environ.get("BACKEND_BASE", "http://api:8001")
METRICS_PATH = os.environ.get("METRICS_PATH", "/metrics")
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set. Check your .env")
DISCORD_APP_ID = os.environ.get("DISCORD_CLIENT_ID")


async def call_backend_query(
    question: str, user_id: str, top_k: int = 5, channel_id: str | None = None
):
    headers = {
        "X-User-ID": user_id,
        "X-Channel-ID": channel_id or "",
        "X-Request-ID": str(uuid.uuid4()),
        "User-Agent": "discord-rag-bot/1.0",
    }
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        # Use query API that saves to database and returns query_id
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
    async with httpx.AsyncClient(timeout=15.0, limits=limits) as client:
        r = await client.post(
            f"{BACKEND_BASE}/api/v1/feedback/submit",
            json={
                "message_id": query_id,
                "user_id": user_id,
                "score": score,
                "comment": comment,
            },
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


async def clear_global_commands():
    """Remove legacy global slash commands to avoid duplicates when using guild scope."""
    if not DISCORD_APP_ID:
        logger.warning("DISCORD_CLIENT_ID not set; skip clearing global commands")
        return
    try:
        api = "https://discord.com/api/v10"
        url = f"{api}/applications/{DISCORD_APP_ID}/commands"
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            # PUT empty list to overwrite all global commands
            r = await client.put(url, headers=headers, json=[])
            r.raise_for_status()
            logger.info("Cleared global application commands (PUT [])")
    except httpx.HTTPError as e:
        logger.warning(f"Failed to clear global commands: {e}")


@BOT.event
async def on_ready():
    """Bot ready event with explicit guild command sync"""
    logger.info("✅ Discord bot connected successfully!")
    logger.info(f"📊 Bot name: {BOT.user.name}")
    logger.info(f"🆔 Bot ID: {BOT.user.id}")
    logger.info(f"🏠 Connected servers: {len(BOT.guilds)}")

    # Print connected servers
    if BOT.guilds:
        logger.info("📋 Connected servers:")
        for guild in BOT.guilds:
            logger.info(f"  - {guild.name} (ID: {guild.id})")

    # Explicitly sync guild commands if GUILD_ID is set
    if GUILD_ID:
        try:
            logger.info(f"🔄 Syncing commands for guild ID: {GUILD_ID}")
            # Ensure no global duplicates linger
            await clear_global_commands()
            await BOT.synchronize_interactions()
            logger.info("✅ Guild commands synced successfully!")
        except Exception as e:
            logger.error(f"❌ Failed to sync guild commands: {e}")

    logger.info("🎉 Bot is ready! Use slash commands in Discord.")
    logger.info("    Available commands: /ping, /ask, /feedback, /health, /config")


FB_UP_EMOJI = os.environ.get(
    "FB_UP_EMOJI_ID", ""
)  # e.g., <:thumbsup:123456789012345678>
FB_DOWN_EMOJI = os.environ.get("FB_DOWN_EMOJI_ID", "")
FB_REGEN_EMOJI = os.environ.get("FB_REGEN_EMOJI_ID", "")

USE_ASSET_EMBEDS = os.environ.get("USE_ASSET_EMBEDS", "true").lower() in {
    "1",
    "true",
    "yes",
}
ASSET_UP = os.environ.get("ASSET_UP_PATH", "assets/thumbs-up.png")
ASSET_DOWN = os.environ.get("ASSET_DOWN_PATH", "assets/thumb-down.png")
ASSET_REGEN = os.environ.get("ASSET_REGEN_PATH", "assets/refresh-page-option.png")


def fb_buttons(query_id: str) -> ActionRow:
    # Fixed custom_ids for reliable exact-match callbacks (library limitation)
    up_kwargs = {"style": ButtonStyle.SECONDARY, "custom_id": "fb_up"}
    down_kwargs = {"style": ButtonStyle.SECONDARY, "custom_id": "fb_down"}
    regen_kwargs = {"style": ButtonStyle.SECONDARY, "custom_id": "fb_regen"}
    # Prefer custom emoji if provided; otherwise label fallback
    if FB_UP_EMOJI:
        up_kwargs["emoji"] = FB_UP_EMOJI
    else:
        up_kwargs["label"] = "👍"
    if FB_DOWN_EMOJI:
        down_kwargs["emoji"] = FB_DOWN_EMOJI
    else:
        down_kwargs["label"] = "👎"
    if FB_REGEN_EMOJI:
        regen_kwargs["emoji"] = FB_REGEN_EMOJI
    else:
        regen_kwargs["label"] = "🔄"
    up = Button(**up_kwargs)
    down = Button(**down_kwargs)
    regen = Button(**regen_kwargs)
    return ActionRow(up, down, regen)  # Use varargs instead of a list


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
        logger.info(f"Backend response payload: {type(payload)} - {payload}")
        answer = payload.get("answer", "[no answer]")
        logger.info(f"Extracted answer: {answer}")
        query_id = payload.get("query_id") or str(uuid.uuid4())  # button fallback id
        logger.info(f"Extracted query_id: {query_id}")
        latency = int((time.perf_counter() - start) * 1000)
        logger.info(f"Latency: {latency}ms")

        # DM or ephemeral fallback
        logger.info("About to create buttons...")
        buttons = fb_buttons(query_id)
        logger.info(f"Created buttons: {type(buttons)}")
        sent = None
        if private:
            try:
                user = await BOT.fetch_user(ctx.author.id)
                sent = await user.send(answer, components=[buttons])
            except Exception:  # Forbidden or other DM errors
                sent = await ctx.send(
                    answer,
                    flags=MessageFlags.EPHEMERAL,
                    components=[buttons],
                )
            except Exception:
                sent = await ctx.send(
                    answer,
                    flags=MessageFlags.EPHEMERAL,
                    components=[buttons],
                )
        else:
            sent = await ctx.send(answer, components=[buttons])
            logger.info(f"Sent message to channel: {sent}")

        # Map Discord message ID → backend query_id and question for follow-up actions
        try:
            if sent and getattr(sent, "id", None):
                MESSAGE_QID[int(sent.id)] = str(query_id)
                MESSAGE_QUESTION[int(sent.id)] = question
                logger.info(f"Stored MESSAGE_QID[{int(sent.id)}] = {query_id}")
        except Exception:
            logger.warning("Could not store message→query mapping")

        # discord_message_id = getattr(sent, "id", None)
        # RAG_TOTAL.inc()  # Commented out due to missing metrics module
        # RAG_LATENCY.observe(latency / 1000.0)  # Commented out due to missing metrics module

    except httpx.HTTPError as e:
        # RAG_TOTAL.inc()  # Commented out due to missing metrics module
        # RAG_FAILURES.inc()  # Commented out due to missing metrics module
        # fail latency also aggregate (meaningful)
        # RAG_LATENCY.observe((time.perf_counter() - start) / 1000.0)  # Commented out due to missing metrics module
        logger.error(f"HTTP error in /ask command: {e}")
        await ctx.send(
            "❌ **Service Unavailable**\n\n"
            "The backend service is not responding. Please try again later.\n"
            "If this problem persists, contact an administrator.",
            flags=MessageFlags.EPHEMERAL,
        )

    except Exception as e:
        # RAG_TOTAL.inc()  # Commented out due to missing metrics module
        # RAG_FAILURES.inc()  # Commented out due to missing metrics module
        # RAG_LATENCY.observe((time.perf_counter() - start) / 1000.0)  # Commented out due to missing metrics module
        logger.error(f"Unexpected error in /ask command: {e}")
        await ctx.send(
            "❌ **Query Error**\n\n"
            "An unexpected error occurred while processing your question.\n"
            "Please try again later or rephrase your question.",
            flags=MessageFlags.EPHEMERAL,
        )


@component_callback("fb_up")
async def on_fb_up(ctx: ComponentContext):
    try:
        await ctx.defer(ephemeral=True)
        msg_id = int(getattr(ctx.message, "id", 0) or 0)
        query_id = MESSAGE_QID.get(msg_id)
        if not query_id:
            await ctx.send(
                "This button has expired. Please run /ask again.",
                flags=MessageFlags.EPHEMERAL,
            )
            return
        logger.info(
            f"Calling backend feedback (up) for user {ctx.author.id}, qid={query_id}"
        )
        await call_backend_feedback(
            query_id=query_id,
            user_id=str(ctx.author.id),
            score="up",
            comment=None,
        )
        logger.info("Backend feedback call successful (up)")
        await ctx.send("Thanks for the feedback 👍", flags=MessageFlags.EPHEMERAL)
    except httpx.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        text = None
        try:
            if getattr(e, "response", None) is not None:
                text = e.response.text
        except Exception:
            text = None
        logger.error(
            f"HTTP error in feedback processing (up): status={status} body={text}"
        )
        if status == 400 and text and "already submitted" in text.lower():
            await ctx.send(
                "You've already submitted feedback for this message.",
                flags=MessageFlags.EPHEMERAL,
            )
        elif status == 400 and text and "query not found" in text.lower():
            await ctx.send(
                "This button has expired. Please run /ask again.",
                flags=MessageFlags.EPHEMERAL,
            )
        else:
            await ctx.send(
                "Backend is not responding. Please try again later.",
                flags=MessageFlags.EPHEMERAL,
            )
    except Exception as e:
        logger.error(f"Unexpected error in feedback processing (up): {e}")
        await ctx.send(
            "An error occurred while processing your feedback.",
            flags=MessageFlags.EPHEMERAL,
        )


@component_callback("fb_down")
async def on_fb_down(ctx: ComponentContext):
    try:
        await ctx.defer(ephemeral=True)
        msg_id = int(getattr(ctx.message, "id", 0) or 0)
        query_id = MESSAGE_QID.get(msg_id)
        if not query_id:
            await ctx.send(
                "This button has expired. Please run /ask again.",
                flags=MessageFlags.EPHEMERAL,
            )
            return
        logger.info(
            f"Calling backend feedback (down) for user {ctx.author.id}, qid={query_id}"
        )
        await call_backend_feedback(
            query_id=query_id,
            user_id=str(ctx.author.id),
            score="down",
            comment=None,
        )
        logger.info("Backend feedback call successful (down)")
        await ctx.send("Thanks for the feedback 👎", flags=MessageFlags.EPHEMERAL)
    except httpx.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        text = None
        try:
            if getattr(e, "response", None) is not None:
                text = e.response.text
        except Exception:
            text = None
        logger.error(
            f"HTTP error in feedback processing (down): status={status} body={text}"
        )
        if status == 400 and text and "already submitted" in text.lower():
            await ctx.send(
                "You've already submitted feedback for this message.",
                flags=MessageFlags.EPHEMERAL,
            )
        elif status == 400 and text and "query not found" in text.lower():
            await ctx.send(
                "This button has expired. Please run /ask again.",
                flags=MessageFlags.EPHEMERAL,
            )
        else:
            await ctx.send(
                "Backend is not responding. Please try again later.",
                flags=MessageFlags.EPHEMERAL,
            )
    except Exception as e:
        logger.error(f"Unexpected error in feedback processing (down): {e}")
        await ctx.send(
            "An error occurred while processing your feedback.",
            flags=MessageFlags.EPHEMERAL,
        )


@component_callback("fb_regen")
async def on_fb_regen(ctx: ComponentContext):
    try:
        await ctx.defer(ephemeral=True)
        msg_id = int(getattr(ctx.message, "id", 0) or 0)
        question = MESSAGE_QUESTION.get(msg_id)
        if not question:
            await ctx.send(
                "This button has expired. Please run /ask again.",
                flags=MessageFlags.EPHEMERAL,
            )
            return
        # Re-call backend with same question and user
        payload = await call_backend_query(
            question,
            user_id=str(ctx.author.id),
            top_k=5,
            channel_id=str(ctx.channel_id),
        )
        answer = payload.get("answer", "[no answer]")
        # Send a fresh message with buttons bound to new query_id
        new_qid = payload.get("query_id") or str(uuid.uuid4())
        row = fb_buttons(new_qid)
        sent = await ctx.send(answer, flags=MessageFlags.EPHEMERAL, components=[row])
        try:
            if sent and getattr(sent, "id", None):
                MESSAGE_QID[int(sent.id)] = str(new_qid)
                MESSAGE_QUESTION[int(sent.id)] = question
        except Exception:
            logger.warning("Could not store message→query mapping for regen")
    except httpx.HTTPError as e:
        logger.error(f"HTTP error in regenerate: {e}")
        await ctx.send(
            "Backend is not responding. Please try again later.",
            flags=MessageFlags.EPHEMERAL,
        )
    except Exception as e:
        logger.error(f"Unexpected error in regenerate: {e}")
        await ctx.send(
            "An error occurred while regenerating the answer.",
            flags=MessageFlags.EPHEMERAL,
        )


# (Optional) You can add broader diagnostics here if needed.


@slash_command(
    name="health", description="backend health", scopes=[GUILD_ID] if GUILD_ID else None
)
async def health(ctx: SlashContext):
    try:
        async with httpx.AsyncClient(
            timeout=5.0,
            limits=limits,
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
    ) as client:
        r = await client.get(url, headers={"User-Agent": "discord-rag-bot/1.0"})
        r.raise_for_status()
        return r.text


async def get_backend_json(url: str, timeout: float = 10.0) -> dict:
    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
    ) as client:
        r = await client.get(url, headers={"User-Agent": "discord-rag-bot/1.0"})
        r.raise_for_status()
        return r.json()


@slash_command(
    name="feedback",
    description="Get feedback statistics",
    scopes=[GUILD_ID] if GUILD_ID else None,
)
@slash_option(
    name="days",
    description="Number of days to look back (default: 7)",
    opt_type=OptionType.INTEGER,
    required=False,
    min_value=1,
    max_value=365,
)
async def feedback_stats(ctx: SlashContext, days: int = 7):
    """Get feedback statistics for the specified period"""
    await ctx.defer()
    try:
        summary = await get_backend_json(
            f"{BACKEND_BASE}/api/v1/feedback/summary?days={days}"
        )

        lines = [
            f"**Feedback Summary (Last {days} days)**",
            f"**Total Feedback**: {summary.get('total_feedback', 0)}",
            f"**👍 Up Votes**: {summary.get('up_votes', 0)}",
            f"**👎 Down Votes**: {summary.get('down_votes', 0)}",
            f"**Unique Users**: {summary.get('unique_users', 0)}",
            f"**Unique Messages**: {summary.get('unique_messages', 0)}",
            f"**Satisfaction Rate**: {summary.get('satisfaction_rate', 0):.1f}%",
        ]
        await ctx.send("\n".join(lines), flags=MessageFlags.EPHEMERAL)
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting feedback stats: {e}")
        await ctx.send(
            "❌ **Statistics Error**\n\n"
            "The backend service is not responding. Please try again later.\n"
            "If this problem persists, contact an administrator.",
            flags=MessageFlags.EPHEMERAL,
        )
    except Exception as e:
        logger.error(f"Unexpected error getting feedback stats: {e}")
        await ctx.send(
            "❌ **Statistics Error**\n\n"
            "An unexpected error occurred while retrieving feedback statistics.\n"
            "Please try again later.",
            flags=MessageFlags.EPHEMERAL,
        )


@slash_command(
    name="config",
    description="Show backend config & health",
    scopes=[GUILD_ID] if GUILD_ID else None,
)
async def config(ctx: SlashContext):
    await ctx.defer()
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
    await ctx.defer()
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
