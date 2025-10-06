#!/usr/bin/env python3
"""
Discord Slash Commands Registration Script
Direct API call to register guild commands
"""
import os
from pathlib import Path

import requests

# Load environment variables from .env file manually
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

# Discord API configuration
APP_ID = os.getenv("DISCORD_CLIENT_ID")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not all([APP_ID, GUILD_ID, TOKEN]):
    print("❌ Missing required environment variables:")
    print(f"   DISCORD_CLIENT_ID: {APP_ID}")
    print(f"   DISCORD_GUILD_ID: {GUILD_ID}")
    print(f"   DISCORD_BOT_TOKEN: {'Set' if TOKEN else 'Not set'}")
    exit(1)

# Command definitions
commands = [
    {
        "name": "ping",
        "description": "Bot alive check",
        "type": 1,  # CHAT_INPUT
    },
    {
        "name": "ask",
        "description": "RAG chatbot ask question",
        "type": 1,  # CHAT_INPUT
        "options": [
            {
                "type": 3,  # STRING
                "name": "question",
                "description": "ask question",
                "required": True,
            },
            {
                "type": 5,  # BOOLEAN
                "name": "private",
                "description": "DM or channel (default: channel)",
                "required": False,
            },
        ],
    },
    {
        "name": "feedback",
        "description": "Get feedback statistics",
        "type": 1,  # CHAT_INPUT
        "options": [
            {
                "type": 4,  # INTEGER
                "name": "days",
                "description": "Number of days to look back (default: 7)",
                "required": False,
                "min_value": 1,
                "max_value": 365,
            }
        ],
    },
    {
        "name": "health",
        "description": "Backend health check",
        "type": 1,  # CHAT_INPUT
    },
    {
        "name": "config",
        "description": "Show backend config & health",
        "type": 1,  # CHAT_INPUT
    },
]


def register_guild_commands():
    """Register slash commands to specific guild"""
    url = (
        f"https://discord.com/api/v10/applications/{APP_ID}/guilds/{GUILD_ID}/commands"
    )

    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}

    print(f"🔄 Registering commands for guild {GUILD_ID}...")
    print(f"📡 API URL: {url}")
    print(f"🤖 App ID: {APP_ID}")

    try:
        response = requests.put(url, headers=headers, json=commands)

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code in [200, 201]:
            print("✅ Commands registered successfully!")
            print(f"📋 Registered {len(commands)} commands:")
            for cmd in commands:
                print(f"   - /{cmd['name']}: {cmd['description']}")
            print("\n🎉 You can now use slash commands in Discord!")
            print("   Type '/' in your Discord channel to see the commands.")
        else:
            print("❌ Failed to register commands")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Error registering commands: {e}")


def clear_guild_commands():
    """Clear all guild commands"""
    url = (
        f"https://discord.com/api/v10/applications/{APP_ID}/guilds/{GUILD_ID}/commands"
    )

    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}

    print(f"🗑️ Clearing commands for guild {GUILD_ID}...")

    try:
        response = requests.put(url, headers=headers, json=[])

        if response.status_code in [200, 201]:
            print("✅ Commands cleared successfully!")
        else:
            print("❌ Failed to clear commands")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Error clearing commands: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        clear_guild_commands()
    else:
        register_guild_commands()
