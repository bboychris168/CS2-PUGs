# CS2-PUGs Agent Guide

This document is the contributor/operator reference for this repository.

## Purpose
- Discord bot for managing CS2 PUG lobbies and matches.
- Uses DatHost REST APIs for CS2 match orchestration.
- Uses PostgreSQL (`asyncpg`) for guild, lobby, match, and player state.

## Architecture Map
- Entry point: [run.py](run.py)
  - Loads intents from `intents.json`.
  - Creates `G5Bot` and starts it with `asyncio.run`.
- Bot core: [bot/bot.py](bot/bot.py)
  - `setup_hook()` initializes DB pool, DatHost API session, webhook server.
  - `on_ready()` performs one-time guild sync/setup and optional slash-command sync.
  - Cogs are loaded dynamically from `bot/cogs` with `logger.py` loaded first.
- Match/lobby orchestration: [bot/cogs/lobby.py](bot/cogs/lobby.py), [bot/cogs/match.py](bot/cogs/match.py)
- DatHost API wrapper: [bot/helpers/api.py](bot/helpers/api.py)
- Webhook server: [bot/helpers/webhook.py](bot/helpers/webhook.py)
- Database layer: [bot/helpers/db.py](bot/helpers/db.py)

## Startup and Command Sync
- Install dependencies: `pip3 install -r requirements.txt`
- Run DB migrations: `python3 migrate.py up`
- Start bot: `python3 run.py`
- Slash command choice updates are sent during `on_ready()` when `bot.sync_commands_globally` is `true`.
  - If command options look stale in Discord, restart the bot so command sync runs.

## DatHost Integration (Current Behavior)
- Match flow calls `fetch_game_server()` in [bot/cogs/match.py](bot/cogs/match.py).
- The bot fetches DatHost CS2 servers, finds an idle non-booting server, then updates it:
  - `cs2_settings.game_mode`
  - `location`
- The bot then creates a CS2 match on that server.
- If no idle server exists, setup fails with `No game server available at the moment.`
- Important: this codebase currently **does not create DatHost servers from scratch** during match setup.

## CS2 Game Modes
- Lobby game mode options and API type hints currently support:
  - `competitive`
  - `casual`
  - `arms_race`
  - `ffa_deathmatch`
  - `retakes`
  - `wingman`
  - `custom`
- DB enum extension migration: [migrations/20260303_01_game-mode-extend.py](migrations/20260303_01_game-mode-extend.py)

## Webhook Contract
- Routes:
  - `POST /cs2bot-api/match-end`
  - `POST /cs2bot-api/round-end`
- Auth:
  - `Authorization` header required.
  - Accepts either `Bearer <token>` or raw token.
  - Token maps to `matches.api_key`.
- Return behavior includes explicit `401`, `403`, `400`, and `503` cases.
- DatHost callbacks use URLs built from `webserver.host` and `webserver.port` in config.

## Database Conventions
- Route DB access through `DBManager` in [bot/helpers/db.py](bot/helpers/db.py).
- Return model objects via `from_dict` constructors.
- Keep async patterns consistent with existing `asyncpg` usage.
- Prefer parameterized SQL for new work (`$1`, `$2`, ...).
- Do not introduce additional string-concatenated SQL in new code.

## Security and Ops
- Treat `config.json` as secret material.
  - Discord token, DatHost credentials, DB credentials, and webhook host values are sensitive.
- Never commit real secrets.
- If secrets are exposed, rotate immediately.
- Ensure DatHost can reach the webhook server at configured host/port.

## Contributor Workflow
- Keep changes focused and minimal.
- Preserve existing model and cog patterns.
- Update or add migrations for schema changes (do not edit applied migrations).
- Validate operationally after behavior changes:
  - migration applies
  - bot starts
  - commands sync
  - match setup and webhooks still function
