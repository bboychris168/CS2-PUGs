# Project Guidelines

Reference: [AGENT.md](AGENT.md) is the full project runbook. This file is the concise coding policy for Copilot changes.

## Code Style
- Follow existing async patterns (`async`/`await`, `aiohttp`, `asyncpg`) as in [bot/helpers/api.py](bot/helpers/api.py) and [bot/helpers/db.py](bot/helpers/db.py).
- Preserve model construction style (`from_dict`, Discord objects on model fields), e.g. [bot/helpers/models/lobby.py](bot/helpers/models/lobby.py) and [bot/helpers/models/match.py](bot/helpers/models/match.py).
- Reuse computed properties for stats where available (e.g., rating/KDR patterns in stats models) instead of duplicating formulas.

## Architecture
- Entry point: [run.py](run.py) loads `intents.json`, creates `G5Bot`, and starts via `asyncio.run`.
- Startup sequence in [bot/bot.py](bot/bot.py): DB connect → API session connect → webhook server start → guild sync/setup → optional global command sync.
- Cogs load dynamically from `bot/cogs` with `logger.py` first.
- Webhooks are served by [bot/helpers/webhook.py](bot/helpers/webhook.py) at:
	- `POST /cs2bot-api/match-end`
	- `POST /cs2bot-api/round-end`

## DatHost Integration
- API wrapper is [bot/helpers/api.py](bot/helpers/api.py) using `aiohttp` BasicAuth.
- Match setup currently selects from existing idle CS2 servers (`get_game_servers`) and configures them (`update_game_server`).
- Do not assume server auto-provisioning during match setup; if no idle server is available, setup fails.
- Supported `game_mode` values in current code:
	- `competitive`, `casual`, `arms_race`, `ffa_deathmatch`, `retakes`, `wingman`, `custom`

## Database and Migrations
- Route DB operations through `DBManager` in [bot/helpers/db.py](bot/helpers/db.py).
- Return model objects via `from_dict` where appropriate.
- For new SQL, prefer parameterized queries (`$1`, `$2`, ...) and avoid introducing additional string-built SQL.
- Add new migrations for schema changes; do not edit previously applied migration files.
- Base schema enums are in [migrations/20211226_01_aVejE-create-base-tables.py](migrations/20211226_01_aVejE-create-base-tables.py), and game mode extension is in [migrations/20260303_01_game-mode-extend.py](migrations/20260303_01_game-mode-extend.py).

## Build and Validation
- Install deps: `pip3 install -r requirements.txt`
- Run migrations: `python3 migrate.py up`
- Start bot: `python3 run.py`
- There is no documented automated test suite; validate by targeted runtime checks for changed behavior.
- If slash command choices changed, restart bot so command sync runs in `on_ready`.

## Security
- Treat `config.json` as sensitive (Discord token, DatHost credentials, DB credentials, webhook-related settings).
- Never commit secrets.
- Webhook auth is enforced via `Authorization` token matched to `matches.api_key` in [bot/helpers/webhook.py](bot/helpers/webhook.py).
