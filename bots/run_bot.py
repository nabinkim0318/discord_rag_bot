#!/usr/bin/env python3
"""
Discord bot execution script
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from interactions import Client, Intents

# add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# load environment variables from project root

load_dotenv(project_root / ".env")


async def main():
    """Discord bot main execution function"""

    # check environment variables
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ DISCORD_BOT_TOKEN environment variable is not set.")
        print("💡 Add DISCORD_BOT_TOKEN to .env file.")
        return

    guild_id = os.getenv("GUILD_ID")
    backend_base = os.getenv("BACKEND_BASE", "http://localhost:8001")

    print("🤖 Discord RAG Bot starting...")
    print(f"🔑 Token: {token[:10]}...{token[-10:]}")
    print(f"🏠 Guild ID: {guild_id or 'Global'}")
    print(f"🔗 Backend: {backend_base}")

    # create bot client
    bot = Client(
        intents=Intents.DEFAULT | Intents.GUILD_MESSAGES,
        sync_interactions=True,
        asyncio_debug=True,
    )

    @bot.event
    async def on_ready():
        """when bot is ready"""
        print("✅ Discord bot connected successfully!")
        print(f"📊 Bot name: {bot.user.name}")
        print(f"🆔 Bot ID: {bot.user.id}")
        print(f"🏠 Connected servers: {len(bot.guilds)}")

        # print connected servers
        if bot.guilds:
            print("📋 Connected servers:")
            for guild in bot.guilds:
                print(f"  - {guild.name} (ID: {guild.id})")

        print("🎉 Bot is ready! Use slash commands in Discord.")
        print(
            "    Available commands: /ping, /ask, /feedback, /health, /config, /metrics"
        )

    @bot.event
    async def on_error(event, *args, **kwargs):
        """when error occurs"""
        print(f"❌ Bot error: {event}")
        import traceback

        traceback.print_exc()

    try:
        # start bot
        await bot.astart(token)
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped.")
    except Exception as e:
        print(f"❌ Bot execution failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped.")
        sys.exit(0)
