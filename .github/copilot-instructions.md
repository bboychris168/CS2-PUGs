# Project Guidelines

## Code Style
- Follow existing async patterns (async/await, aiohttp, asyncpg) as shown in [bot/helpers/api.py](bot/helpers/api.py) and [bot/helpers/db.py](bot/helpers/db.py).
- Models use `from_dict` constructors and store Discord objects directly; keep this pattern in model classes like [bot/helpers/models/guild.py](bot/helpers/models/guild.py) and [bot/helpers/models/match.py](bot/helpers/models/match.py).
- Prefer computed properties on stats models (e.g., `kdr`, `rating`) instead of re-deriving metrics; see [bot/helpers/models/playerstats.py](bot/helpers/models/playerstats.py).

## Architecture
- Entry point loads intents from `intents.json`, creates `G5Bot`, and starts via `asyncio.run`; see [run.py](run.py).
- Bot startup connects DB pool, starts API session and webhook server, syncs guild data, then syncs commands; see [bot/bot.py](bot/bot.py).
- Cogs are dynamically loaded from bot/cogs with logger first; see [bot/bot.py](bot/bot.py).
- Webhook server exposes match-end and round-end endpoints and updates match state and embeds; see [bot/helpers/webhook.py](bot/helpers/webhook.py).

## Build and Test
- Install deps: `pip3 install -r requirements.txt`.
- Run migrations: `python3 migrate.py up`.
- Start bot: `python3 run.py`.
- Repo setup (PostgreSQL, config copy, DB role) is documented in [README.md](README.md).
- No automated test commands are documented.

## Project Conventions
- DB access goes through `DBManager` and returns model objects via `from_dict`; see [bot/helpers/db.py](bot/helpers/db.py).
- Enum-like values for rules (team_method, captain_method, map_method, game_mode, team) are defined in schema migrations; see [migrations/20211226_01_aVejE-create-base-tables.py](migrations/20211226_01_aVejE-create-base-tables.py).
- Webhook auth uses an Authorization bearer token to look up matches by `api_key`; see [bot/helpers/webhook.py](bot/helpers/webhook.py) and [bot/helpers/db.py](bot/helpers/db.py).

## Integration Points
- Discord bot uses `discord.py` AutoShardedBot and specific intents; see [bot/bot.py](bot/bot.py) and setup notes in [README.md](README.md).
- DatHost API integration uses `aiohttp` with BasicAuth and webhook setup; see [bot/helpers/api.py](bot/helpers/api.py).
- Database is PostgreSQL via asyncpg with yoyo migrations; see [bot/helpers/db.py](bot/helpers/db.py) and [migrations/20211226_01_aVejE-create-base-tables.py](migrations/20211226_01_aVejE-create-base-tables.py).

## Security
- Secrets/config (DB credentials, DatHost auth, webhook bearer token) are loaded from config; treat config.json as sensitive per [bot/helpers/db.py](bot/helpers/db.py) and [bot/helpers/api.py](bot/helpers/api.py).
- Webhook endpoints validate Authorization header before updates; see [bot/helpers/webhook.py](bot/helpers/webhook.py).
