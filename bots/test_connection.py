#!/usr/bin/env python3
"""
Discord bot connection test script
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from interactions import Client, Intents

# add project root to Python path
project_root = Path(__file__).parent.parent
print(project_root)
sys.path.insert(0, str(project_root))

# load environment variables from project root
print(project_root / ".env")
load_dotenv(project_root / ".env")


async def test_discord_connection():
    """Discord bot connection test"""

    # get token from environment variable
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ DISCORD_BOT_TOKEN environment variable is not set.")
        print("💡 Add DISCORD_BOT_TOKEN to .env file.")
        return False

    print("🔍 Discord bot connection test started...")
    print(f"🔑 Token: {token[:10]}...{token[-10:]}")

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
        else:
            print("⚠️  Bot is not invited to any servers.")

        # close bot
        await bot.close()

    @bot.event
    async def on_error(event, *args, **kwargs):
        """when error occurs"""
        print(f"❌ Bot error: {event}")
        import traceback

        traceback.print_exc()

    try:
        # start bot (timeout 30 seconds)
        print("🚀 Start bot...")
        await asyncio.wait_for(bot.astart(token), timeout=30.0)
        return True

    except asyncio.TimeoutError:
        print("⏰ Bot connection timeout (30 seconds)")
        return False
    except Exception as e:
        print(f"❌ Bot connection failed: {e}")
        return False


async def test_backend_connection():
    """test backend server connection"""
    import httpx

    backend_url = os.getenv("BACKEND_BASE", "http://localhost:8001")
    print(f"\n🔍 Test backend server connection: {backend_url}")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{backend_url}/api/v1/health/")
            if response.status_code == 200:
                data = response.json()
                print("✅ Backend server connection successful!")
                print(f"📊 Status: {data.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Backend server response error: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Backend server connection failed: {e}")
        return False


async def main():
    """main test function"""
    print("🤖 Discord RAG Bot connection test")
    print("=" * 50)

    # test backend connection
    backend_ok = await test_backend_connection()

    # Discord bot connection test
    discord_ok = await test_discord_connection()

    print("\n" + "=" * 50)
    print("📋 Test result summary:")
    print(
        f"  Backend server: {'✅ Connected' if backend_ok else '❌ Connection failed'}"
    )
    print(f"  Discord bot: {'✅ Connected' if discord_ok else '❌ Connection failed'}")

    if backend_ok and discord_ok:
        print("\n🎉 All services connected successfully!")
        return True
    else:
        print("\n⚠️ Some services have problems.")
        return False


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted.")
        sys.exit(1)
