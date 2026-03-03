import logging
from aiohttp import web

from bot.helpers.api import Match
from bot.resources import Config
from bot.helpers.utils import generate_leaderboard_img, generate_scoreboard_img


class WebServer:
    _instance = None  # Class variable to store the single instance

    def __new__(cls, bot):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, bot):
        if getattr(self, 'initialized', False):
            return
        self.initialized = True  # Ensure initialization only once
        self.server_running = False
        self.bot = bot
        self.logger = logging.getLogger("API")
        self.host = Config.webserver_host
        self.port = Config.webserver_port
        self.match_cog = self.bot.get_cog("Match")

    @staticmethod
    def _extract_api_key(req):
        auth_header = req.headers.get('Authorization')
        if not auth_header:
            return None

        bearer_prefix = 'Bearer '
        if auth_header.startswith(bearer_prefix):
            return auth_header[len(bearer_prefix):].strip()

        return auth_header.strip()

    async def match_end(self, req):
        self.logger.info(f"Received webhook data from {req.url}")
        self.match_cog = self.match_cog or self.bot.get_cog("Match")
        api_key = self._extract_api_key(req)
        if not api_key:
            return web.json_response({'error': 'Unauthorized'}, status=401)

        match_model = await self.bot.db.get_match_by_api_key(api_key)
        if not match_model:
            return web.json_response({'error': 'Invalid webhook token'}, status=403)

        try:
            resp_data = await req.json()
        except Exception:
            return web.json_response({'error': 'Invalid JSON body'}, status=400)

        match_api = Match.from_dict(resp_data)
        if not match_api:
            return web.json_response({'error': 'Invalid match payload'}, status=400)
        if not self.match_cog:
            self.logger.error('Match cog is not loaded while handling match-end webhook')
            return web.json_response({'error': 'Match service unavailable'}, status=503)

        try:
            if match_model.game_server_id != 'simulation':
                await self.bot.api.stop_game_server(match_model.game_server_id)
        except Exception as e:
            self.logger.error(e, exc_info=1)

        guild_model = await self.bot.db.get_guild_by_id(match_model.guild.id)
        if match_model.game_server_id != 'simulation':
            match_api = await self.bot.api.get_match(match_model.id)
            if not match_api:
                return web.json_response({'error': 'Unable to fetch match from DatHost'}, status=502)
        await self.match_cog.finalize_match(match_model, match_api, guild_model)
        return web.json_response({'ok': True})

    async def round_end(self, req):
        self.logger.debug(f"Received webhook data from {req.url}")
        self.match_cog = self.match_cog or self.bot.get_cog("Match")
        api_key = self._extract_api_key(req)
        if not api_key:
            return web.json_response({'error': 'Unauthorized'}, status=401)

        match_model = await self.bot.db.get_match_by_api_key(api_key)
        if not match_model:
            return web.json_response({'error': 'Invalid webhook token'}, status=403)

        try:
            resp_data = await req.json()
        except Exception:
            return web.json_response({'error': 'Invalid JSON body'}, status=400)

        match_api = Match.from_dict(resp_data)
        if not match_api:
            return web.json_response({'error': 'Invalid match payload'}, status=400)

        if self.match_cog:
            await self.match_cog.process_round_update(match_model, match_api)

        return web.json_response({'ok': True})

    async def start_webhook_server(self):
        if self.server_running:
            self.logger.warning("Webhook server is already running.")
            return

        self.logger.info(f'Starting webhook server on {self.host}:{self.port}')

        app = web.Application()

        app.router.add_post("/cs2bot-api/match-end", self.match_end)
        app.router.add_post("/cs2bot-api/round-end", self.round_end)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, host=self.host, port=self.port)

        try:
            await site.start()
            self.server_running = True
            self.logger.info("Webhook server started and running in the background")
        except Exception as e:
            self.logger.error("Failed to start the webhook server.", exc_info=1)
            self.server_running = False
