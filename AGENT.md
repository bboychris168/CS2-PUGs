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

### DatHost API Endpoints Used
Implementation in [bot/helpers/api.py](bot/helpers/api.py) using `aiohttp.ClientSession` with BasicAuth:
- `GET /api/0.1/game-servers` - List all game servers
- `GET /api/0.1/game-servers/{id}` - Get specific server details
- `PUT /api/0.1/game-servers/{id}` - Update server settings (location, game_mode)
- `POST /api/0.1/game-servers/{id}/stop` - Stop server
- `POST /api/0.1/cs2-matches` - Create new CS2 match
- `GET /api/0.1/cs2-matches/{id}` - Get match details
- `PUT /api/0.1/cs2-matches/{id}/players` - Add player to match
- `POST /api/0.1/cs2-matches/{id}/cancel` - Cancel match

### Server Locations (27 Available)
North America (6): `newyork`, `losangeles`, `miami`, `chicago`, `seattle`, `dallas`, `canada`  
Europe (11): `denmark`, `finland`, `france`, `germany`, `netherlands`, `poland`, `spain`, `sweden`, `turkey`, `uk`  
Asia/Pacific (6): `australia`, `hongkong`, `india`, `japan`, `singapore`  
Other (2): `brazil`, `southafrica`

## Ready-Up Flow
Pre-match confirmation system implemented in [bot/views/readyView.py](bot/views/readyView.py):

1. **Trigger**: When lobby reaches capacity, ready-up view is posted
2. **UI**: Buttons for "Ready" and "Unready" with live participant count
3. **Timeout**: Players have limited time to ready up
4. **Validation**: Match setup only proceeds if all players ready
5. **Cleanup**: Unready players moved to waiting room
6. **State**: Tracked in-memory via view instance (not persisted to DB)

## CS2 Game Modes
- Lobby game mode options and API type hints currently support:
  - `competitive` - Standard 5v5 competitive
  - `casual` - Casual gameplay
  - `arms_race` - Arms Race progression mode
  - `ffa_deathmatch` - Free-for-all deathmatch
  - `retakes` - Retake practice mode
  - `wingman` - 2v2 wingman
  - `custom` - Custom configuration
- DB enum extension migration: [migrations/20260303_01_game-mode-extend.py](migrations/20260303_01_game-mode-extend.py)
- Added in migration: `casual`, `arms_race`, `ffa_deathmatch`, `retakes`, `custom` (2026-03-03)

## Map Selection Methods
Configured per lobby via `map_method` field. DB enum values: `random`, `veto`, `poll`.

### Random
- Selects random map from configured map pool via `random.choice()`
- No user interaction required
- Fast, suitable for quick matches

### Veto
- Interactive captain-based map elimination
- Implemented in [bot/views/vetoView.py](bot/views/vetoView.py)
- Captains alternate removing maps via button UI
- Last remaining map is selected
- Respects captain order from team selection

### Poll (NEW: 2026-03-03)
- Discord native poll voting system
- Implementation: [bot/views/pollView.py](bot/views/pollView.py)
- Migration: [migrations/20260303_02_poll-map-method.py](migrations/20260303_02_poll-map-method.py)
- **Technical Details**:
  - Creates `discord.Poll` with 1-hour minimum duration (Discord API requirement)
  - Force-ends poll after `POLL_DURATION_SECS = 60` seconds via `end_poll()`
  - Live countdown updates match setup embed every 10 seconds
  - Displays map display names from `Config.maps` as poll answers
  - Tie-breaking: random selection from maps with max votes
  - Returns map key (e.g., `de_mirage`) from display name reverse lookup
  - Fallback: random map if poll has no answers (edge case)

## Team Selection Methods
Configured per lobby via `team_method` field. DB enum values: `random`, `autobalance`, `captains`.

### Random
- Shuffles players and splits into two teams
- No skill consideration
- Fast setup

### Autobalance
- Algorithm balances teams by player rating
- Fetches player stats from `player_stats` table
- Uses computed `rating` property from [bot/helpers/models/playerstats.py](bot/helpers/models/playerstats.py)
- Weighted formula combines K/D ratio, win rate, HSP, multi-kills, MVP rate
- Iteratively assigns players to maintain rating balance

### Captains
- Interactive team picking via [bot/views/teamsView.py](bot/views/teamsView.py)
- Captain selection controlled by `captain_method`:
  - `random` - Random selection from lobby
  - `rank` - Highest rated players become captains
  - `volunteer` - Players volunteer, random if multiple/none
- Captains alternate picking players via button UI
- Pick order: A, B, B, A, A, B... (snake draft)

## Slash Commands Reference
All commands implemented as `app_commands` in cogs:

### Lobby Management (Administrator Only)
- `/create-lobby` - Create lobby with full configuration ([bot/cogs/lobby.py](bot/cogs/lobby.py))
  - Params: `capacity`, `game_mode`, `connect_time`, `teams_method`, `captains_method`, `map_method`
  - Creates voice channel with permissions for linked role
  - Capacity options: 1 (simulation), 2, 4, 6, 8, 10, 12
- `/delete-lobby` - Delete lobby and voice channel ([bot/cogs/lobby.py](bot/cogs/lobby.py))
- `/empty-lobby` - Remove all users from lobby queue ([bot/cogs/lobby.py](bot/cogs/lobby.py))

### Spectator Management
- `/add-spectator` - Add user to spectators list ([bot/cogs/lobby.py](bot/cogs/lobby.py))
  - Inserts into `spectators` table with `(user_id, lobby_id)` FK
  - Spectators auto-added to match on setup
- `/remove-spectator` - Remove spectator ([bot/cogs/lobby.py](bot/cogs/lobby.py))
- `/spectators-list` - Display spectators for lobby ([bot/cogs/lobby.py](bot/cogs/lobby.py))

### Player Management
- `/link-steam` - Link Discord to Steam ([bot/cogs/link.py](bot/cogs/link.py))
  - Accepts: Steam ID64, profile URL, or vanity URL
  - Grants "Linked" role
  - Updates `users` table
- `/view-stats` - View player statistics ([bot/cogs/stats.py](bot/cogs/stats.py))
  - Fetches from `player_stats` table
  - Optional `user` param for viewing others' stats
  - Generates statistics image via PIL
- `/reset-stats` - Reset personal stats ([bot/cogs/stats.py](bot/cogs/stats.py))
  - Deletes row from `player_stats` table

### Match Management (Administrator Only)
- `/cancel-match` - Cancel live match ([bot/cogs/match.py](bot/cogs/match.py))
  - Calls DatHost `cancel_match()` API
  - Cleans up match channels/roles
- `/add-player` - Add player to live match ([bot/cogs/match.py](bot/cogs/match.py))
  - Params: `match_id`, `user`, `team` (team1/team2/spectator)
  - Calls DatHost `add_match_player()` API
- `/sim-round` - Trigger simulated round update ([bot/cogs/match.py](bot/cogs/match.py))
  - Only works for simulation matches (`game_server_id = 'simulation'`)
  - Posts fake round-end payload to webhook handler

### Utility
- `/help` - Paginated help system ([bot/cogs/help.py](bot/cogs/help.py))
  - Interactive page navigation

## Spectator System
- **Database**: `spectators` table with `(user_id, lobby_id)` FKs
- **Integration**: Spectators auto-added to DatHost match on setup
- **Commands**: Add, remove, list spectators per lobby
- **Match behavior**: Spectators can connect to server but don't affect teams/stats
- **Cleanup**: Cascade delete when lobby is deleted

## Statistics System
- **Database**: `player_stats` table tracks per-user metrics
- **Tracked Metrics**:
  - Basic: kills, deaths, assists, MVPs, headshots, score
  - Multi-kills: `kills_2`, `kills_3`, `kills_4`, `kills_5`
  - Aggregates: `total_rounds`, `wins`, `total_matches`
- **Computed Properties** (from [bot/helpers/models/playerstats.py](bot/helpers/models/playerstats.py)):
  - `kdr` - Kills/Deaths ratio
  - `hsp` - Headshot percentage
  - `win_rate` - Wins/Total matches
  - `rating` - Weighted sum formula: `(kdr * 1.0 + assist_rate * 0.7 + hsp * 0.2 + mvp_rate * 0.4 + k2_rate * 0.6 + k3_rate * 3.0 + k4_rate * 5.0 + k5_rate * 10.0 + win_rate * 1.5) / 2`
  - Various rate calculations: `assist_rate`, `mvp_rate`, `k2_rate`, `k3_rate`, `k4_rate`, `k5_rate` (all per round played)
- **Update Flow**: Webhook `match-end` updates stats atomically via SQL `UPDATE ... SET column = column + $N`
- **Image Generation**: PIL-based statistics card rendering with custom fonts/templates
- **Leaderboard**: Auto-updates leaderboard channel with top players by rating

## Simulation Mode (Testing)
Activated when lobby `capacity = 1`. Allows testing without DatHost servers.

### Behavior
- No DatHost server required (`game_server_id = 'simulation'`)
- Match setup flow proceeds normally (teams, captains, map selection all work)
- Bot auto-generates 10 simulated rounds with random stats:
  - Random kills/deaths/assists per player
  - Random team scores (0-16 for each team, sum ≤ 30)
  - Simulated timestamps and round numbers
- Second "player" is bot itself with placeholder stats
- `/sim-round` command manually triggers round updates via webhook handler

### Use Cases
- Testing match flow without server costs
- Debugging webhook handling
- Validating statistics calculations
- Testing UI components (ready-up, veto, poll, teams)

### Technical Details
- Implemented in [bot/cogs/match.py](bot/cogs/match.py) `fetch_game_server()`
- Check: `if lobby.capacity == 1:`
- Creates match with `game_server_id = 'simulation'`
- Generates fake player with bot's user ID + 1
- Round simulation loops through 10 rounds with `asyncio.sleep(1)` delays
- Posts to local webhook endpoint `/cs2bot-api/round-end`

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

## Auto Guild Setup
On bot startup or when joining a new guild, `on_guild_join()` and `on_ready()` trigger automatic setup:

### Created Resources
From [bot/bot.py](bot/bot.py) `setup_guild()`:
1. **Category**: "G5" - Container for all bot-managed channels
2. **Role**: "Linked" - Assigned to users who have linked Steam accounts
3. **Voice Channel**: "Waiting Room" - Default voice channel with permissions for linked role
4. **Text Channels**:
   - "Results" - Bot-only posting of match results (no user send permissions)
   - "Leaderboard" - Bot-only posting of statistics leaderboard

### Database Sync
- Guild record created/updated in `guilds` table
- Stores channel IDs, category ID, and role ID for future reference

## Match Resource Management
Dynamically created/cleaned up per match:

### Created on Match Setup
- **Category**: `"Match #{match_id}"` - Container for match channels
- **Team Voice Channels**: Team A and Team B voice channels with move restrictions
- **Team Roles**: Temporary roles for team assignment (used for channel permissions)
- **Permissions**: Only team members can connect to their team channel

### Player Movement
- Players automatically moved to team voice channels on match start
- Spectators moved to appropriate channel or remain in waiting room

### Cleanup on Match End
- Category and all child channels deleted
- Team roles removed
- Players moved back to waiting room
- Database: Match status updated, stats recorded

## Database Schema Overview
### Tables
- `guilds` - Guild configuration and resource IDs
- `lobbies` - Active lobby configuration and state
- `lobby_users` - Many-to-many relationship for lobby participants
- `matches` - Active match state and DatHost IDs
- `users` - Discord-to-Steam account mappings
- `player_stats` - Aggregate player statistics
- `spectators` - Lobby spectator assignments

### Enums (PostgreSQL)
- `game_mode` - competitive, casual, arms_race, ffa_deathmatch, retakes, wingman, custom
- `team_method` - captains, autobalance, random
- `captain_method` - random, rank, volunteer
- `map_method` - random, veto, poll
- `team` - team1, team2

### Key Relationships
- `lobbies.guild` → `guilds.guild_id` (CASCADE)
- `matches.lobby` → `lobbies.lobby_id` (CASCADE)
- `lobby_users.lobby_id` → `lobbies.lobby_id` (CASCADE)
- `spectators.lobby_id` → `lobbies.lobby_id` (CASCADE)
- `player_stats.user_id` → `users.user_id` (CASCADE on user deletion)

## Troubleshooting

### Common Issues

#### Commands Not Syncing
**Symptom**: Slash command choices outdated or missing  
**Solution**:
- Set `bot.sync_commands_globally: true` in config
- Restart bot to trigger `on_ready()` command sync
- Check logs for sync errors
- Verify bot has `applications.commands` scope

#### Webhook Not Receiving Data
**Symptom**: Round/match updates not arriving  
**Solution**:
- Verify `webserver.host` and `webserver.port` are accessible from internet
- Check DatHost callback URL configuration
- Verify `Authorization` header matches `matches.api_key`
- Check firewall/NAT rules allow inbound traffic
- Review bot logs for 401/403/400/503 responses
- Test webhook endpoint manually with curl

#### No Game Server Available
**Symptom**: Match setup fails with "No game server available"  
**Solution**:
- Verify DatHost account has active CS2 servers
- Check that at least one server is idle (not in-use or booting)
- Review DatHost server status in dashboard
- Check `config.json` DatHost credentials are valid
- Enable `debug: true` to see API responses

#### Match Not Starting
**Symptom**: Players in team channels but match doesn't begin  
**Solution**:
- Verify all players connected to DatHost server
- Check `connect_time` hasn't expired
- Review DatHost match status API
- Check webhook server is reachable
- Verify no firewall blocking DatHost → webhook connection

#### Statistics Not Updating
**Symptom**: `/view-stats` shows old or zero data  
**Solution**:
- Verify webhook `match-end` endpoint is reachable
- Check `player_stats` table in database
- Review bot logs for SQL errors
- Ensure `users` table has Steam ID linked
- Verify Steam IDs match between DatHost and bot database

#### Database Migration Failures
**Symptom**: `python3 migrate.py up` fails  
**Solution**:
- Check PostgreSQL service is running
- Verify database credentials in `config.json`
- Ensure database user has CREATE/ALTER permissions
- Review migration file syntax
- Check for conflicting migrations (never edit applied migrations)
- For enum additions, migrations use `ADD VALUE IF NOT EXISTS` (safe to re-run)

## Contributor Workflow
- Keep changes focused and minimal.
- Preserve existing model and cog patterns.
- Update or add migrations for schema changes (do not edit applied migrations).
- Validate operationally after behavior changes:
  - migration applies
  - bot starts
  - commands sync
  - match setup and webhooks still function

### Code Style Guidelines
- **Async patterns**: Use `async`/`await` consistently with `aiohttp` and `asyncpg`
- **Model construction**: Use `from_dict` classmethod pattern for DB row → model object
- **Computed properties**: Reuse existing `@property` methods in stats models rather than recalculating
- **SQL queries**: Prefer parameterized queries (`$1`, `$2`, ...) over string concatenation
- **Error handling**: Use try/except for API calls and DB operations, log errors appropriately
- **Discord objects**: Pass Discord objects (guild, member, channel) to models rather than IDs when available

### Adding New Features
1. **Database changes**: Create new migration file in `migrations/` directory
2. **Model updates**: Add/update models in `bot/helpers/models/` with `from_dict` constructor
3. **DB methods**: Add queries to `DBManager` in `bot/helpers/db.py`
4. **Command implementation**: Add slash command to appropriate cog in `bot/cogs/`
5. **Views/UI**: Create interactive UI in `bot/views/` if needed
6. **Testing**: Test with simulation mode (`capacity=1`) before production

### Migration Best Practices
- Use `yoyo` framework conventions
- Name format: `YYYYMMDD_NN_description.py`
- Never edit migrations that have been applied
- For enum additions: `ALTER TYPE enum_name ADD VALUE IF NOT EXISTS 'value';`
- Include rollback steps where possible (enums cannot be rolled back in PostgreSQL)
- Test migrations on local DB before committing

## Recent Changes (2026-03-03)

### Game Mode Extension
**Migration**: [migrations/20260303_01_game-mode-extend.py](migrations/20260303_01_game-mode-extend.py)  
**Added**: 5 new game modes to support more CS2 gameplay variants
- `casual` - Casual gameplay mode
- `arms_race` - Arms Race progression
- `ffa_deathmatch` - Free-for-all deathmatch
- `retakes` - Retake practice
- `custom` - Custom configurations

**Impact**: `/create-lobby` command now offers all 7 game modes  
**Compatibility**: Existing lobbies/matches unaffected (competitive and wingman remain)

### Poll-Based Map Selection
**Migration**: [migrations/20260303_02_poll-map-method.py](migrations/20260303_02_poll-map-method.py)  
**Added**: `poll` value to `map_method` enum  
**Implementation**: [bot/views/pollView.py](bot/views/pollView.py)

**Features**:
- Discord native poll voting (1-hour duration, force-ended at 60s)
- Live countdown updates every 10 seconds
- Players vote on maps from configured pool
- Tie-breaking via random selection
- Display names from `Config.maps` used in poll

**Impact**: Admins can now create lobbies with democratic map selection  
**UI**: Native Discord poll interface with vote counts visible to all players  
**Fallback**: Random selection if poll fails or has no votes

### Technical Improvements
- All map selection methods now fully documented
- Statistics system with computed rating formula
- Spectator system with dedicated database table
- Simulation mode for testing without DatHost servers
- Comprehensive error handling and logging throughout cogs
