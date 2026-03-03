# bot/helpers/api.py

import asyncio
import logging
import json
import aiohttp
from typing import Literal, Optional, List
from bot.resources import Config
from bot.helpers.errors import APIError


class MatchPlayer:
    def __init__(self, data):
        stats = data.get('stats') or {}
        steam_id = data.get('steam_id_64') or data.get('steam_id')
        if steam_id is None:
            raise KeyError('steam_id_64')

        self.match_id = data.get('match_id')
        self.steam_id = int(steam_id)
        self.team = data.get('team', 'none')
        self.kills = int(stats.get('kills', 0))
        self.assists = int(stats.get('assists', 0))
        self.headshots = int(stats.get('kills_with_headshot', 0))
        self.deaths = int(stats.get('deaths', 0))
        self.mvps = int(stats.get('mvps', 0))
        self.k2 = int(stats.get('2ks', 0))
        self.k3 = int(stats.get('3ks', 0))
        self.k4 = int(stats.get('4ks', 0))
        self.k5 = int(stats.get('5ks', 0))
        self.score = int(stats.get('score', 0))

    @classmethod
    def from_dict(cls, data: dict) -> Optional["MatchPlayer"]:
        try:
            return cls(data)
        except (TypeError, KeyError, ValueError):
            return None
    
    @property
    def to_dict(self) -> dict:
        return {
            'kills': self.kills,
            'deaths': self.deaths,
            'assists': self.assists,
            'headshots': self.headshots,
            'mvps': self.mvps,
            'k2': self.k2,
            'k3': self.k3,
            'k4': self.k4,
            'k5': self.k5,
            'score': self.score
        }


class Match:
    """"""

    def __init__(self, match_data: dict) -> None:
        """"""
        self.id = match_data['id']
        team1 = match_data.get('team1') or {}
        team2 = match_data.get('team2') or {}
        team1_stats = team1.get('stats') or {}
        team2_stats = team2.get('stats') or {}
        settings = match_data.get('settings') or {}

        self.game_server_id = match_data.get('game_server_id')
        self.team1_name = team1.get('name', 'team1')
        self.team2_name = team2.get('name', 'team2')
        self.team1_score = int(team1_stats.get('score', 0))
        self.team2_score = int(team2_stats.get('score', 0))
        self.canceled = match_data.get('cancel_reason') is not None
        self.finished = bool(match_data.get('finished', False))
        self.connect_time = int(settings.get('connect_time', 0))
        self.map_name = settings.get('map', 'unknown')
        self.rounds_played = int(match_data.get('rounds_played', 0))
        self.players = []
        for player in match_data.get('players', []):
            parsed_player = MatchPlayer.from_dict(player)
            if parsed_player:
                self.players.append(parsed_player)

    @classmethod
    def from_dict(cls, data: dict) -> Optional["Match"]:
        try:
            return cls(data)
        except (TypeError, KeyError, ValueError):
            return None
    
    @property
    def winner(self):
        if self.canceled or not self.finished:
            return 'none'
        return 'team1' if self.team1_score > self.team2_score else 'team2'
    
    @property
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'game_server_id': self.game_server_id,
            'team1_name': self.team1_name,
            'team2_name': self.team2_name,
            'team1_score': self.team1_score,
            'team2_score': self.team2_score,
            'canceled': self.canceled,
            'finished': self.finished,
            'map_name': self.map_name,
            'connect_time': self.connect_time,
            'rounds_played': self.rounds_played,
            'players': self.players,
            'winner': self.winner
        }


class GameServer:
    """"""

    def __init__(self, data: dict) -> None:
        """"""
        ports = data.get('ports') or {}
        cs2_settings = data.get('cs2_settings') or {}

        self.id = data['id']
        self.name = data.get('name', '')
        self.ip = data.get('ip', '')
        self.port = ports.get('game')
        self.gotv_port = ports.get('gotv')
        self.on = bool(data.get('on', False))
        self.game_mode = cs2_settings.get('game_mode')
        self.match_id = data.get('match_id')
        self.booting = bool(data.get('booting', False))

    @classmethod
    def from_dict(cls, data: dict) -> Optional["GameServer"]:
        try:
            return cls(data)
        except (TypeError, KeyError, ValueError):
            return None


async def start_request_log(session, ctx, params):
    """"""
    ctx.start = asyncio.get_event_loop().time()
    logger = logging.getLogger('API')
    logger.debug(f'Sending {params.method} request to {params.url}')


async def end_request_log(session, ctx, params):
    """"""
    logger = logging.getLogger('API')
    elapsed = asyncio.get_event_loop().time() - ctx.start
    logger.debug(f'Response received from {params.url} ({elapsed:.2f}s)\n'
                f'    Status: {params.response.status}\n'
                f'    Reason: {params.response.reason}')
    try:
        resp_json = await params.response.json()
        logger.debug(f'Response JSON from {params.url}: {resp_json}')
    except Exception as e:
        pass


TRACE_CONFIG = aiohttp.TraceConfig()
TRACE_CONFIG.on_request_start.append(start_request_log)
TRACE_CONFIG.on_request_end.append(end_request_log)


class APIManager:
    """ Class to contain API request wrapper functions. """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("API")

    def connect(self):
        self.logger.info('Starting API helper client session')
        self.session = aiohttp.ClientSession(
            base_url="https://dathost.net",
            auth=aiohttp.BasicAuth(Config.dathost_email, Config.dathost_password),
            json_serialize=lambda x: json.dumps(x, ensure_ascii=False),
            timeout=aiohttp.ClientTimeout(total=30),
            trace_configs=[TRACE_CONFIG] if Config.debug else None
        )

    async def _parse_json_response(self, resp, default_message: str):
        try:
            return await resp.json(content_type=None)
        except Exception:
            body = await resp.text()
            raise APIError(f"{default_message}. Unexpected non-JSON response: {body[:250]}")

    async def _raise_api_error(self, resp, default_message: str) -> None:
        if resp.status == 401:
            raise APIError("Invalid DatHost credentials!")

        message = default_message
        try:
            resp_data = await resp.json()
            if isinstance(resp_data, dict):
                message = resp_data.get('message') or resp_data.get('error') or message
        except Exception:
            try:
                resp_text = await resp.text()
                if resp_text:
                    message = resp_text
            except Exception:
                pass

        raise APIError(f"{message} (HTTP {resp.status})")

    async def close(self):
        """ Close the API helper's session. """
        self.logger.info('Closing API helper client session')
        await self.session.close()

    async def get_game_server(self, game_server_id: str) -> "GameServer":
        """"""
        url = f"/api/0.1/game-servers/{game_server_id}"

        async with self.session.get(url=url) as resp:
            if not resp.ok:
                await self._raise_api_error(resp, "Failed to get game server")
            resp_data = await self._parse_json_response(resp, "Failed to decode game server response")
            if not isinstance(resp_data, dict):
                raise APIError("Unexpected DatHost game server response.")
            game_server = GameServer.from_dict(resp_data)
            if not game_server:
                raise APIError("Unexpected DatHost game server response.")
            return game_server
        
    async def get_game_servers(self) -> List[GameServer]:
        """"""
        url = f"/api/0.1/game-servers"

        async with self.session.get(url=url) as resp:
            if not resp.ok:
                await self._raise_api_error(resp, "Failed to get game servers")
            resp_data = await self._parse_json_response(resp, "Failed to decode game servers response")
            if not isinstance(resp_data, list):
                raise APIError("Unexpected DatHost game servers response.")
            game_servers = []
            for game_server in resp_data:
                if game_server.get('game') != 'cs2':
                    continue
                parsed_game_server = GameServer.from_dict(game_server)
                if parsed_game_server:
                    game_servers.append(parsed_game_server)
            return game_servers
        
    async def update_game_server(
        self,
        server_id: str,
        game_mode: Literal["competitive", "casual", "arms_race", "ffa_deathmatch", "retakes", "wingman", "custom"]=None,
        location: str=None,
    ):
        """"""
        url = f"/api/0.1/game-servers/{server_id}"
        payload = {}
        if game_mode: payload["cs2_settings.game_mode"] = game_mode
        if location: payload["location"] = location

        async with self.session.put(url=url, data=payload) as resp:
            if not resp.ok:
                await self._raise_api_error(resp, "Failed to update game server")
            return True
        
    async def stop_game_server(self, server_id: str):
        """"""
        url = f"/api/0.1/game-servers/{server_id}/stop"

        async with self.session.post(url=url) as resp:
            if not resp.ok:
                await self._raise_api_error(resp, "Failed to stop game server")
            return True

    async def get_match(self, match_id: str) -> Optional["Match"]:
        """"""
        url = f"/api/0.1/cs2-matches/{match_id}"

        async with self.session.get(url=url) as resp:
            if resp.status == 404:
                return None
            if not resp.ok:
                await self._raise_api_error(resp, "Failed to get match")
            resp_data = await self._parse_json_response(resp, "Failed to decode match response")
            if not isinstance(resp_data, dict):
                raise APIError("Unexpected DatHost match response.")
            match = Match.from_dict(resp_data)
            if not match:
                raise APIError("Unexpected DatHost match response.")
            return match
        
    async def create_match(
        self,
        game_server_id: str,
        map_name: str,
        team1_name: str,
        team2_name: str,
        match_players: List[dict],
        connect_time,
        api_key: str,
    ) -> Match:
        """"""

        url = "/api/0.1/cs2-matches"

        payload = {
            'game_server_id': game_server_id,
            'team1': { 'name': 'team_' + team1_name },
            'team2': { 'name': 'team_' + team2_name },
            'players': match_players,
            'settings': {
                'map': map_name,
                'connect_time': connect_time,
                'match_begin_countdown': 15
            },
            'webhooks': {
                'match_end_url': f'http://{Config.webserver_host}:{Config.webserver_port}/cs2bot-api/match-end',
                'round_end_url': f'http://{Config.webserver_host}:{Config.webserver_port}/cs2bot-api/round-end',
                'authorization_header': f'Bearer {api_key}'
            }
        }

        async with self.session.post(url=url, json=payload) as resp:
            if not resp.ok:
                await self._raise_api_error(resp, "Failed to create match")
            resp_data = await self._parse_json_response(resp, "Failed to decode create-match response")
            if not isinstance(resp_data, dict):
                raise APIError("Unexpected DatHost create-match response.")
            match = Match.from_dict(resp_data)
            if not match:
                raise APIError("Unexpected DatHost create-match response.")
            return match

    async def add_match_player(
        self,
        match_id: int,
        steam_id: int,
        team: Literal["team1", "team2", "spectator"],
    ):
        """"""
        url = f"/api/0.1/cs2-matches/{match_id}/players"
        payload = {
            'steam_id_64': str(steam_id),
            'team': team,
        }

        async with self.session.put(url=url, json=payload) as resp:
            if resp.status == 404:
                raise APIError("Invalid match ID.")
            if not resp.ok:
                await self._raise_api_error(resp, "Failed to add player to match")
            resp_data = await self._parse_json_response(resp, "Failed to decode add-player response")
            if not isinstance(resp_data, dict):
                raise APIError("Unexpected DatHost add-player response.")
            player = MatchPlayer.from_dict(resp_data)
            if not player:
                raise APIError("Unexpected DatHost add-player response.")
            return player
                
    async def cancel_match(self, match_id: int):
        """"""
        url = f"/api/0.1/cs2-matches/{match_id}/cancel"

        async with self.session.post(url=url) as resp:
            if resp.status == 404:
                raise APIError("Invalid match ID.")
            if not resp.ok:
                await self._raise_api_error(resp, "Failed to cancel match")
            resp_data = await self._parse_json_response(resp, "Failed to decode cancel-match response")
            if not isinstance(resp_data, dict):
                raise APIError("Unexpected DatHost cancel-match response.")
            match = Match.from_dict(resp_data)
            if not match:
                raise APIError("Unexpected DatHost cancel-match response.")
            return match
