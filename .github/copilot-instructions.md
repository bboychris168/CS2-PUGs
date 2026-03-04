# Project Guidelines

Reference: [AGENT.md](AGENT.md) is the full project runbook. This file is the concise coding policy for Copilot changes.

## Code Style
- Follow existing async patterns (`async`/`await`, `aiohttp`, `asyncpg`) as in [bot/helpers/api.py](bot/helpers/api.py) and [bot/helpers/db.py](bot/helpers/db.py).
- Preserve model construction style (`from_dict`, Discord objects on model fields), e.g. [bot/helpers/models/lobby.py](bot/helpers/models/lobby.py) and [bot/helpers/models/match.py](bot/helpers/models/match.py).
- Reuse computed properties for stats where available (e.g., rating/KDR/HSP/win_rate patterns in [bot/helpers/models/playerstats.py](bot/helpers/models/playerstats.py)) instead of duplicating formulas.

## Architecture
- Entry point: [run.py](run.py) loads `intents.json`, creates `G5Bot`, and starts via `asyncio.run`.
- Startup sequence in [bot/bot.py](bot/bot.py): DB connect → API session connect → webhook server start → guild sync/setup → optional global command sync.
- Cogs load dynamically from `bot/cogs` with `logger.py` first.
- Webhooks are served by [bot/helpers/webhook.py](bot/helpers/webhook.py) at:
	- `POST /cs2bot-api/match-end` - Final match results and statistics updates
	- `POST /cs2bot-api/round-end` - Live round-by-round updates

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
- Base schema enums are in [migrations/20211226_01_aVejE-create-base-tables.py](migrations/20211226_01_aVejE-create-base-tables.py).
- Recent migrations:
	- [migrations/20260303_01_game-mode-extend.py](migrations/20260303_01_game-mode-extend.py) - Extended game mode enum
	- [migrations/20260303_02_poll-map-method.py](migrations/20260303_02_poll-map-method.py) - Added poll map selection

## Feature-Specific Patterns

### Map Selection Methods
Database enum `map_method` values: `random`, `veto`, `poll`
- **Random**: Simple `random.choice()` from map pool
- **Veto**: Interactive button UI in [bot/views/vetoView.py](bot/views/vetoView.py) - captains alternate removing maps
- **Poll** (NEW): Discord native poll in [bot/views/pollView.py](bot/views/pollView.py)
	- Uses `discord.Poll` with 1-hour duration (API minimum), force-ended at 60s
	- Live countdown updates match setup embed every 10s
	- Tie-breaking via `random.choice()` from max-voted maps
	- Maps display names → keys via `Config.maps` reverse lookup

### Team Selection Methods
Database enum `team_method` values: `random`, `autobalance`, `captains`
- **Random**: Shuffle and split
- **Autobalance**: Balance by player rating from `player_stats` table using computed `rating` property
- **Captains**: Interactive picking via [bot/views/teamsView.py](bot/views/teamsView.py)
	- Captain selection via `captain_method`: `random`, `rank`, `volunteer`
	- Snake draft pick order: A, B, B, A, A, B...

### Statistics System
- Table: `player_stats` with aggregate metrics (kills, deaths, assists, mvps, headshots, k2, k3, k4, k5, rounds_played, wins, total_matches)
- Model: [bot/helpers/models/playerstats.py](bot/helpers/models/playerstats.py) with computed properties:
	- `kdr` - K/D ratio
	- `hsp` - Headshot percentage
	- `win_rate` - Win/match ratio
	- `rating` - Complex weighted sum: `(kdr * 1.0 + assist_rate * 0.7 + hsp * 0.2 + mvp_rate * 0.4 + k2_rate * 0.6 + k3_rate * 3.0 + k4_rate * 5.0 + k5_rate * 10.0 + win_rate * 1.5) / 2`
	- Rate properties: `assist_rate`, `mvp_rate`, `k2_rate`, `k3_rate`, `k4_rate`, `k5_rate` (per round played)
- Updates via webhook `match-end` using atomic SQL: `UPDATE ... SET column = column + $N`
- Never recalculate rating in queries; use model's `@property` method

### Spectator System
- Table: `spectators` with `(user_id, lobby_id)` FKs, CASCADE on lobby delete
- Commands: `/add-spectator`, `/remove-spectator`, `/spectators-list` in [bot/cogs/lobby.py](bot/cogs/lobby.py)
- Integration: Spectators auto-added to DatHost match on setup
- Match behavior: Can connect to server but don't affect teams/stats

### Ready-Up Flow
- View: [bot/views/readyView.py](bot/views/readyView.py) with "Ready"/"Unready" buttons
- Triggered when lobby reaches capacity
- Match setup only proceeds if all players ready
- Unready players moved to waiting room
- State tracked in-memory (not in DB)

## Build and Validation
- Install deps: `pip3 install -r requirements.txt`
- Run migrations: `python3 migrate.py up`
- Start bot: `python3 run.py`
- There is no documented automated test suite; validate by targeted runtime checks for changed behavior.
- If slash command choices changed (e.g., new enum values), restart bot so command sync runs in `on_ready`.
- Use a 1vs1 lobby (`capacity=2`) for testing the full match workflow end-to-end

## Security
- Treat `config.json` as sensitive (Discord token, DatHost credentials, DB credentials, webhook-related settings).
- Never commit secrets.
- Webhook auth is enforced via `Authorization` header matched to `matches.api_key` in [bot/helpers/webhook.py](bot/helpers/webhook.py).
