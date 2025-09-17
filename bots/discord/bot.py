# bots/discord/bot.py
# import asyncio
import os
import time
import uuid

import interactions

# from config import SETTINGS
from core.logging import logger
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

from backend.db import insert_feedback, insert_message, update_message_response

# from rag_client import query_rag

GUILD_ID = int(os.environ.get("DISCORD_TEST_GUILD_ID", "0"))
logger.info(f"Bot starting with guild ID: {GUILD_ID if GUILD_ID else 'None'}")

if GUILD_ID:
    BOT = interactions.Client(
        token=os.environ["DISCORD_BOT_TOKEN"],
        default_scope=[GUILD_ID],  # register commands immediately in this guild
    )
else:
    BOT = interactions.Client(token=os.environ["DISCORD_BOT_TOKEN"])
logger.info(f"Bot initialized with guild ID: {GUILD_ID if GUILD_ID else 'None'}")


def query_rag(question: str) -> str:
    return f"[stub] You asked: {question}"


def fb_buttons(message_uuid: str) -> ActionRow:
    up = Button(
        style=ButtonStyle.SUCCESS, label="👍", custom_id=f"fb:{message_uuid}:up"
    )
    down = Button(
        style=ButtonStyle.DANGER, label="👎", custom_id=f"fb:{message_uuid}:down"
    )
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
    await ctx.defer()  # thinking

    start = time.perf_counter()
    msg_id = str(uuid.uuid4())

    # DB record
    insert_message(
        id=msg_id,
        user_id=str(ctx.author.id),
        channel_id=str(ctx.channel_id),
        question=question,
        private=private,
    )

    try:
        # RAG call
        answer = query_rag(question)  # if synchronous, consider thread executor/async
        latency = int((time.perf_counter() - start) * 1000)

        # response path: DM/channel/ephemeral
        sent = None
        if private:
            # DM try
            logger.info(f"Sending DM to {ctx.author.id}")
            try:
                user = await BOT.fetch_user(ctx.author.id)
                sent = await user.send(answer, components=fb_buttons(msg_id))
            except Forbidden:
                logger.error(f"Failed to send DM to {ctx.author.id} (Forbidden)")
                sent = await ctx.send(
                    answer, flags=MessageFlags.EPHEMERAL, components=fb_buttons(msg_id)
                )
            except Exception:
                logger.error(f"Failed to send DM to {ctx.author.id}")
                # DM not possible ephemeral
                sent = await ctx.send(
                    answer, flags=MessageFlags.EPHEMERAL, components=fb_buttons(msg_id)
                )
        else:
            # channel public
            sent = await ctx.send(answer, components=fb_buttons(msg_id))

        discord_message_id = getattr(sent, "id", None)
        update_message_response(
            id=msg_id,
            response=answer,
            discord_message_id=str(discord_message_id) if discord_message_id else None,
            latency_ms=latency,
            status="success",
        )
        RAG_TOTAL.inc()
        RAG_LATENCY.observe(latency / 1000.0)

    except Exception as e:
        update_message_response(
            id=msg_id,
            response=None,
            error=str(e),
            status="error",
        )
        RAG_TOTAL.inc()
        RAG_FAILURES.inc()
        await ctx.send(
            "Sorry, I can't answer your question right now. Please try again later.",
            flags=MessageFlags.EPHEMERAL,
        )


@component_callback("fb:")
async def on_feedback_btn(ctx: ComponentContext):
    # custom_id example: "fb:<uuid>:up"
    try:
        _, message_uuid, score = ctx.custom_id.split(":")
        insert_feedback(
            message_id=message_uuid,
            user_id=str(ctx.author.id),
            score="up" if score == "up" else "down",
            comment=None,
        )
        await ctx.send("Thank you for your feedback!", flags=MessageFlags.EPHEMERAL)
    except Exception:
        await ctx.send("Error processing feedback.", flags=MessageFlags.EPHEMERAL)


@slash_command(
    name="feedback",
    description="feedback for response",
    scopes=[GUILD_ID] if GUILD_ID else None,
)
@slash_option(
    name="message_id",
    description="feedback target message UUID",
    required=True,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="score",
    description="👍 or 👎",
    required=True,
    choices=[{"name": "👍", "value": "up"}, {"name": "👎", "value": "down"}],
    opt_type=OptionType.STRING,
)
@slash_option(
    name="comment",
    description="select comment",
    required=False,
    opt_type=OptionType.STRING,
)
async def feedback(ctx: SlashContext, message_id: str, score: str, comment: str = None):
    try:
        insert_feedback(
            message_id=message_id,
            user_id=str(ctx.author.id),
            score=score,
            comment=comment,
        )
        await ctx.send("Thank you for your feedback!", flags=MessageFlags.EPHEMERAL)
    except Exception:
        await ctx.send("Error saving feedback.", flags=MessageFlags.EPHEMERAL)


@slash_command(
    name="health",
    description="RAG/backend health check",
    scopes=[GUILD_ID] if GUILD_ID else None,
)
async def health(ctx: SlashContext):
    # simply: RAG ping, DB ping etc.
    ok_rag = True
    ok_db = True
    msg = f"RAG: {'OK' if ok_rag else 'DOWN'} | DB: {'OK' if ok_db else 'DOWN'}"
    await ctx.send(msg, flags=MessageFlags.EPHEMERAL)


# @slash_command(name="config", description="check config/connected data sources",
# scopes=[GUILD_ID] if GUILD_ID else None)
# async def config(ctx: SlashContext):
#     sources = SETTINGS.DATA_SOURCES  # example: ["Confluence",
# "GDrive","GitHub"]
#     await ctx.send(f"Connected data sources: {', '.join(sources)}",
# flags=MessageFlags.EPHEMERAL)


# async def config(ctx: SlashContext, private: bool = False):
#     sources = SETTINGS.DATA_SOURCES  # example: ["Confluence","GDrive","GitHub"]
#     await ctx.send(f"Connected data sources:
# {', '.join(sources)}", flags=MessageFlags.EPHEMERAL)

if __name__ == "__main__":
    BOT.start()
