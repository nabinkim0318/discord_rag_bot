#!/usr/bin/env python3
"""
Discord bot execution script
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from interactions import Client, Intents

# Set up basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from root .env file
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)


async def main():
    """Discord bot main execution function"""

    # check environment variables
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.warning("❌ DISCORD_BOT_TOKEN environment variable is not set.")
        logger.warning("💡 Add DISCORD_BOT_TOKEN to .env file.")
        return

    guild_id = os.getenv("GUILD_ID")
    backend_base = os.getenv("BACKEND_BASE", "http://localhost:8001")

    logger.info("🤖 Discord RAG Bot starting...")
    logger.info(f"🔑 Token: {token[:10]}...{token[-10:]}")
    logger.info(f"🏠 Guild ID: {guild_id or 'Global'}")
    logger.info(f"🔗 Backend: {backend_base}")

    # create bot client
    bot = Client(
        intents=Intents.DEFAULT | Intents.GUILD_MESSAGES,
        sync_interactions=True,
        asyncio_debug=True,
    )

    @bot.event
    async def on_ready():
        """when bot is ready"""
        logger.info("✅ Discord bot connected successfully!")
        logger.info(f"📊 Bot name: {bot.user.name}")
        logger.info(f"🆔 Bot ID: {bot.user.id}")
        logger.info(f"🏠 Connected servers: {len(bot.guilds)}")

        # print connected servers
        if bot.guilds:
            logger.info("📋 Connected servers:")
            for guild in bot.guilds:
                logger.info(f"  - {guild.name} (ID: {guild.id})")

        logger.info("🎉 Bot is ready! Use slash commands in Discord.")
        logger.info(
            "    Available commands: /ping, /ask, /feedback, /health, /config, /metrics"
        )

    @bot.event
    async def on_error(event, *args, **kwargs):
        """when error occurs"""
        logger.warning(f"❌ Bot error: {event}")
        import traceback

        traceback.print_exc()

    try:
        # start bot
        await bot.astart(token)
    except KeyboardInterrupt:
        logger.info("\n⏹️ Bot stopped.")
    except Exception as e:
        logger.warning(f"❌ Bot execution failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped.")
        sys.exit(0)
