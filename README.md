# CS2 PUGs Bot

A feature-rich Discord bot for managing Counter-Strike 2 pick-up games (PUGs). Integrates with [DatHost CS2 Servers API](https://dathost.net/reference/cs2-servers-rest-api) for automated match orchestration, player statistics tracking, and comprehensive lobby management.

## ✨ Features

- **🎮 Multiple Game Modes** - Competitive, Casual, Wingman, Arms Race, Retakes, FFA Deathmatch, and Custom
- **🗳️ Flexible Map Selection** - Choose maps via Discord poll voting, captain veto system, or random selection
- **👥 Smart Team Building** - Autobalanced teams by rating, captain drafts, or random assignment
- **📊 Player Statistics** - Track kills, deaths, assists, MVPs, headshots, multi-kills, and calculated ratings
- **👀 Spectator System** - Add spectators who can observe matches without playing
- **🤖 Simulation Mode** - Test match flows without DatHost servers (solo capacity lobbies)
- **🏆 Leaderboards** - Automated leaderboard and statistics display with generated images
- **⚡ Real-time Updates** - Live round and match statistics via DatHost webhooks
- **🔒 Auto Guild Setup** - Automatic creation of required roles, channels, and categories

## 🧪 Test Bot
If you wish to test the bot without any setup, feel free to [invite it](https://discord.com/oauth2/authorize?client_id=820447661932019734&permissions=2433788944&scope=applications.commands+bot) to your Discord server.

## Setup

1. Install PostgreSQL 9.5 or higher.

   ```
   sudo apt-get install postgresql
   ```

2. Clone the project to your server
   ```
   git clone https://github.com/thboss/g5-discord-bot
   ```

3. Install the necessary libraries.
   ```
   pip3 install -r requirements.txt
   ```

4. Run the psql tool with `sudo -u postgres psql` and create a database by running the following commands:

   ```sql
   CREATE ROLE "g5" WITH LOGIN PASSWORD 'yourpassword';
   CREATE DATABASE "g5" OWNER g5;
   ```

   - Be sure to replace `yourpassword` with your own password.

   - Quit psql with `\q`

5. Create and edit the configuration file (`config.json`) in the project root.
   ```
   cp config.json.template config.json
   ```

   **Configuration Sections:**
   - `bot` - Discord bot token, guild ID, command sync settings, debug mode, and map pool
   - `dathost` - DatHost account credentials (email/password)
   - `webserver` - Webhook server host and port for DatHost callbacks
   - `db` - PostgreSQL database connection details

    **Example Configuration:**

    ```json
    {
       "bot": {
          "prefix": "!",
          "token": "YOUR_DISCORD_BOT_TOKEN",
          "guild_id": 123456789012345678,
          "sync_commands_globally": true,
          "debug": false,
          "maps": {
             "de_dust2": "Dust II",
             "de_inferno": "Inferno",
             "de_vertigo": "Vertigo",
             "de_overpass": "Overpass",
             "de_mirage": "Mirage",
             "de_nuke": "Nuke",
             "de_ancient": "Ancient",
             "de_anubis": "Anubis",
             "de_train": "Train"
          }
       },
       "dathost": {
          "email": "YOUR_DATHOST_EMAIL",
          "password": "YOUR_DATHOST_PASSWORD"
       },
       "webserver": {
          "host": "0.0.0.0",
          "port": 3000
       },
       "db": {
          "user": "g5",
          "password": "yourpassword",
          "database": "g5",
          "host": "localhost",
          "port": "5432"
       }
    }
    ```

   **Configuration Notes:**
   - Set `sync_commands_globally` to `true` to sync slash commands on bot startup
   - Enable `debug` for detailed API request logging
   - Map pool can be customized; keys must match CS2 map names
   - The bot will automatically generate required Discord channels and roles on startup

6. Apply the database migrations
   ```
   python3 migrate.py up
   ```

7. Finally, start the bot
   ```
   python3 run.py
   ```


## 📋 Requirements
- **Python 3.11+**
- **PostgreSQL 9.5+**
- **DatHost Account** with at least one available CS2 game server (idle and not in a match)
- **Discord Bot** with the following enabled:
  - **Intents**: Server Members Intent, Message Content Intent
  - **Permissions**: Manage Roles, Manage Channels, Manage Messages, Send Messages, Read Message/View Channels, Attach Files, Use Slash Commands, Connect, Move Members

## 📖 Commands Reference

All commands are slash commands. Type `/` in Discord to see available commands.

### Lobby Management (Administrator Only)

| Command | Parameters | Description |
|---------|-----------|-------------|
| `/create-lobby` | `capacity`, `game_mode`, `connect_time`, `teams_method`, `captains_method`, `map_method` | Create a new lobby with specified settings |
| `/delete-lobby` | `lobby_id` | Delete an existing lobby |
| `/empty-lobby` | `lobby_id` | Remove all players from a lobby |

**Lobby Configuration Options:**
- **Capacity**: 1 (simulation mode), 2, 4, 6, 8, 10, or 12 players
- **Game Mode**: `competitive`, `casual`, `wingman`, `arms_race`, `ffa_deathmatch`, `retakes`, or `custom`
- **Connect Time**: 1-10 minutes before match cancellation if players don't join
- **Teams Method**: 
  - `captains` - Captains pick teams interactively
  - `autobalance` - Algorithm balances by player rating
  - `random` - Random team assignment
- **Captains Method** (if captains mode): `random`, `rank` (highest rated), or `volunteer`
- **Map Method**:
  - `poll` - Discord native poll voting (60 seconds, tie-breaking via random)
  - `veto` - Captains alternate removing maps until one remains
  - `random` - Random map selection

### Player Management

| Command | Parameters | Description |
|---------|-----------|-------------|
| `/link-steam` | `steam_id_or_url` | Link your Discord account to Steam (supports Steam ID, profile URL, or vanity URL) |
| `/view-stats` | `user` (optional) | View your statistics or another player's stats |
| `/reset-stats` | - | Reset your personal statistics |

**Statistics Tracked:**
- Kills, deaths, assists, MVPs, headshots
- Multi-kills (2K, 3K, 4K, 5K)
- Win rate, K/D ratio, headshot percentage
- Overall rating (weighted formula combining KDR, assist rate, HSP, MVP rate, multi-kill rates, win rate)

### Spectator Management

| Command | Parameters | Description |
|---------|-----------|-------------|
| `/add-spectator` | `user`, `lobby_id` | Add a user to lobby as spectator |
| `/remove-spectator` | `user`, `lobby_id` | Remove a user from spectators list |
| `/spectators-list` | `lobby_id` | View all spectators for a lobby |

### Match Management (Administrator Only)

| Command | Parameters | Description |
|---------|-----------|-------------|
| `/cancel-match` | `match_id` | Cancel an active match |
| `/add-player` | `match_id`, `user`, `team` | Add player to live match on specific team or as spectator |
| `/sim-round` | `match_id` | Trigger simulated round update (simulation mode only) |

### Utility

| Command | Description |
|---------|-------------|
| `/help` | Display interactive paginated help system |

## 📦 Dependencies & Maintenance

### Installation
- Install all dependencies from [requirements.txt](requirements.txt) for pinned, stable versions
- The paginator dependency is pinned to an immutable Git revision for deterministic installs
- DatHost authentication uses email/password BasicAuth configured in `config.json`

### Database Migrations
- Schema changes are managed via [Yoyo migrations](https://ollycope.com/software/yoyo/latest/)
- **Never edit previously applied migrations** - create new migration files instead
- Recent migrations:
  - `20260303_01` - Extended game mode enum (added casual, arms_race, ffa_deathmatch, retakes, custom)
  - `20260303_02` - Added `poll` option to map selection methods
- Apply migrations with: `python3 migrate.py up`

### Testing
- **No automated test suite** currently available
- Validate changes via targeted runtime checks
- Use simulation mode (`capacity=1` lobbies) for testing without DatHost servers
- If slash command choices change, restart bot to trigger command sync

## 🌐 DatHost Integration

### Server Selection & Configuration
- During match setup, the bot queries all DatHost CS2 servers and selects an idle server
- Selected server is configured with:
  - Game mode (competitive, casual, wingman, etc.)
  - Server location (27 locations available worldwide)
- CS2 match is then created on the configured server via DatHost API

### Important Notes
- **No Auto-Provisioning**: Bot does not create new DatHost servers automatically
- **Idle Server Required**: Match setup fails if no idle server is available
- **Authentication**: Uses BasicAuth with email/password from `config.json`

### Supported Game Modes
| Mode | Description |
|------|-------------|
| `competitive` | Standard 5v5 competitive CS2 |
| `casual` | Casual CS2 gameplay |
| `wingman` | 2v2 wingman mode |
| `arms_race` | Arms Race progression mode |
| `ffa_deathmatch` | Free-for-all deathmatch |
| `retakes` | Retake practice mode |
| `custom` | Custom game mode configuration |

### Available Server Locations
**North America** (6): New York, California, Florida, Illinois, Washington, Texas, Canada  
**Europe** (11): Denmark, Finland, France, Germany, Netherlands, Poland, Spain, Sweden, Turkey, UK  
**Asia/Pacific** (6): Australia, Hong Kong, India, Japan, Singapore  
**Other** (2): Brazil, South Africa

## 🚀 Production Deployment

### Webhook Configuration
DatHost must be able to reach your webhook endpoints for real-time match updates:
- **Match End**: `POST /cs2bot-api/match-end` - Final match results and statistics
- **Round End**: `POST /cs2bot-api/round-end` - Live round-by-round updates

### Server Setup
1. Configure `webserver.host` and `webserver.port` in `config.json`
2. Ensure the bot listens on an accessible address
3. Publish the webhook service to the internet (typically via reverse proxy)

### Reverse Proxy Configuration
If using Nginx, Caddy, Traefik, or similar:
- Forward requests to the bot's webhook port
- **Preserve the `Authorization` header** (required for authentication)
- Consider enabling HTTPS/TLS for security

### Security Considerations
- **Webhook Authentication**: Enforced via `Authorization` header matched to `matches.api_key`
- **Firewall Rules**: Allow inbound traffic to webhook endpoint
- **Secrets Management**: Never commit `config.json` with real credentials
- **NAT Configuration**: Ensure port forwarding if behind NAT

### Troubleshooting
- **Webhooks not arriving**: Verify callback URL configuration, proxy logs, and bot logs
- **401/403 errors**: Check `Authorization` header and `matches.api_key` in config
- **No idle servers**: Ensure you have available DatHost CS2 servers not in use
- **Commands not syncing**: Set `sync_commands_globally: true` and restart bot

### Auto Guild Setup
On bot startup or when joining a new guild, the bot automatically creates:
- **"G5" Category** - Container for all bot channels
- **"Linked" Role** - Granted to users who have linked their Steam account
- **"Waiting Room" Voice Channel** - Default voice channel for players
- **"Results" Text Channel** - Bot-only posting of match results
- **"Leaderboard" Text Channel** - Bot-only posting of player statistics

## 🎮 How to Play

### Initial Setup (One-Time)
1. **Link Your Steam Account** - Use `/link-steam` with your Steam ID, profile URL, or vanity URL
   - This grants you the "Linked" role and enables you to join lobbies
   - You only need to do this once, but can update it anytime

### Joining a Match
1. **Join a Lobby** - Enter any lobby voice channel created by administrators
   - You'll be automatically added to the queue
   - Leave the voice channel to remove yourself from the queue
   
2. **Ready Up** - Once the lobby is full, click the "Ready" button when prompted
   - All players must ready up before match setup proceeds
   - Unready players are moved back to the waiting room

3. **Team & Map Selection** - Depending on lobby configuration:
   - **Poll Map Selection**: Vote for your preferred map in the Discord poll (60 seconds)
   - **Veto Map Selection**: Captains alternate removing maps until one remains
   - **Random**: Map selected automatically
   - **Captain Teams**: Captains take turns picking players
   - **Autobalance**: Teams automatically balanced by player ratings
   - **Random Teams**: Players randomly assigned to teams

4. **Join the Server** - Bot posts connection info and moves players to team voice channels
   - Connect within the configured time limit (default: 5 minutes)
   - Match starts automatically when enough players connect

5. **Play & Track Stats** - Your statistics are automatically tracked
   - View stats anytime with `/view-stats`
   - Check leaderboards in the designated channel
   - Round and match results posted automatically

### For Spectators
- Administrators can add spectators using `/add-spectator`
- Spectators can observe the match without affecting teams or stats
- View spectator lists with `/spectators-list`

### Testing & Development
- **Simulation Mode**: Create a lobby with `capacity=1` to test without DatHost servers
  - Bot generates simulated rounds with random statistics
  - Use `/sim-round` to manually trigger round updates
  - Perfect for testing match flow and webhook integrations


## 🤝 Contributing

Contributions are welcome! When contributing:
1. Preserve existing async patterns (`async`/`await`, `aiohttp`, `asyncpg`)
2. Follow model construction conventions (`from_dict` methods)
3. Create new migrations for schema changes (don't edit applied migrations)
4. Keep changes focused and test thoroughly
5. Never commit secrets or credentials

For detailed technical guidelines, see [AGENT.md](AGENT.md) and [.github/copilot-instructions.md](.github/copilot-instructions.md).

## 📄 License & Credits

### Thanks To
- [Cameron Shinn](https://github.com/cameronshinn) for the initial [csgo-league-bot](https://github.com/csgo-league/csgo-league-bot) implementation

---

**Note**: This bot is under active development. For technical operator documentation, see [AGENT.md](AGENT.md).

