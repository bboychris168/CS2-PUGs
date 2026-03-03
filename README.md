# CS2 PUGs Bot

A Discord bot to manage CS2 PUGs. Connects to the [DatHost CS2 Servers API](https://dathost.net/reference/cs2-servers-rest-api).

Match setup currently selects from existing idle DatHost CS2 servers, updates server settings, and then creates the match.

## Test
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

   - Required top-level sections: `bot`, `dathost`, `webserver`, `db`
   - `dathost` must contain valid DatHost account credentials.
   - `bot.sync_commands_globally` should be `true` if you want slash-command updates synced on startup.

    Minimal example:

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
             "de_ancient": "Ancient"
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

6. Apply the database migrations
   ```
   python3 migrate.py up
   ```

7. Finally, start the bot
   ```
   python3 run.py
   ```


## Requirements
- Python 3.11+
- DatHost account.
- At least one available CS2 DatHost game server (idle and not currently in a match).
- You must enable **Server Members Intent** and **Message Content Intent** on your bot developers portal.
- Required Permissions:
  - Manage Roles
  - Manage Channels
  - Manage Messages
  - Send Messages
  - Read Message/View Channels
  - Attach Files
  - Use Slash Commands
  - Connect
  - Move Members

## Dependency maintenance
- Install dependencies from [requirements.txt](requirements.txt) to use pinned conservative ranges for runtime stability.
- The bot currently authenticates to DatHost with email/password BasicAuth configured in `config.json`.
- The paginator dependency is pinned to an immutable Git revision for deterministic installs.

## DatHost behavior
- During match setup, the bot fetches all DatHost CS2 game servers and picks an idle server.
- It updates selected server settings such as location and `cs2_settings.game_mode`, then creates the CS2 match.
- If no idle server is available, match setup fails.
- Supported game modes in this bot:
   - `competitive`
   - `casual`
   - `arms_race`
   - `ffa_deathmatch`
   - `retakes`
   - `wingman`
   - `custom`

## Production notes
- DatHost must be able to reach your webhook endpoints:
   - `POST /cs2bot-api/match-end`
   - `POST /cs2bot-api/round-end`
- Set `webserver.host`/`webserver.port` to values where your bot listens, then publish that service to the internet.
- If running behind a reverse proxy (Nginx/Caddy/Traefik), forward requests to the bot webhook port and preserve the `Authorization` header.
- Ensure firewall/NAT rules allow inbound traffic to the published webhook endpoint.
- If webhook events do not arrive, verify the callback URL DatHost received, proxy logs, and bot logs.

## How to play
- **Create lobby:** Create a lobby using command `/create-lobby` (You can create unlimited number of lobbies as you need)
   - Note: This command requires Administrator permissions.
- **Link Steam:** To participate in lobbies, link your Steam account with the command `/link-steam`. This will grant you the Linked role, indicating you’re ready to join lobbies.
   - You need to link your account only once, but you can reuse this command to change you linked steam.
- **Join Lobby:** Simply, join the lobby voice channel, and bot will automatically add you to the queue.
   - Leave the lobby channel to remove from the queue.
- **Match Setup:** Once the lobby is full, the bot will automatically handle the game setup and notify all players as well as create teams channels, ensuring each player is moved to their respective channel.


## Thanks To

1. [Cameron Shinn](https://github.com/cameronshinn) for his initial implementation of [csgo-league-bot](https://github.com/csgo-league/csgo-league-bot).

