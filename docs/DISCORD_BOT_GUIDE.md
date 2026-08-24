# Discord bot

The bot is an **`interactions.py`** client (`interactions.py>=5.12.0` in `bots/discord/requirements.txt`). It is not discord.py.

Source: [`bots/discord/bot.py`](../bots/discord/bot.py).

## What it does

- Slash commands talk to the FastAPI backend (`/api/query/`, health, feedback summary, metrics).
- RAG answers can include **👍 / 👎 / regenerate** buttons.
- Button → `query_id` mapping is an in-process TTL/size-bounded map ([`bots/discord/message_map.py`](../bots/discord/message_map.py)). Restarts and TTL expiry produce "this button has expired".
- Discord user id is sent as feedback `user_id` for duplicate detection. That is **not** authentication.
- Optional Prometheus exporter on port **9109**. Compose scrapes it only with [`docker-compose.discord.yaml`](../docker-compose.discord.yaml).

The bot does not keep a durable conversation store. It does not use reaction emoji collectors; feedback is **message components**.

## Commands

| Command | Behavior |
| --- | --- |
| `/ping` | Liveness; ephemeral `pong` |
| `/ask question:… private:…` | RAG via `POST /api/query/`; optional ephemeral reply; feedback buttons when `query_id` exists |
| `/health` | Backend liveness (`GET /api/v1/health/`) |
| `/feedback days:…` | Aggregate summary (`GET /api/v1/feedback/summary`) |
| `/config` | Selected backend config/health fields |
| `/metrics` | Short metrics snapshot from the backend |

Buttons: `fb_up`, `fb_down`, `fb_regen`. Regen asks the same question again (ephemeral).

## Run locally

```bash
cp env.template .env
# set DISCORD_BOT_TOKEN (and DISCORD_GUILD_ID if you scope commands to one guild)
make docker-up-with-bot
```

Or, with the API already reachable:

```bash
cd bots/discord
pip install -r requirements.txt
python bot.py
```

The bot container has no published host port. Metrics are scraped on the Docker network as `bot:9109` when the overlay is applied.

## What not to expect

- Persistent button state across process restarts
- Per-user feedback history APIs
- Logging of message content as a product feature
- discord.py APIs or cogs
