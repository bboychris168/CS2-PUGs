# match.py

from discord.ext import commands
from discord import Embed, Member, Message, Guild, PermissionOverwrite, SelectOption, VoiceChannel, app_commands, Interaction
from typing import List, Literal

from random import choice, shuffle, randint
import asyncio
import time

from bot.helpers.api import Match
from bot.helpers.utils import GAME_SERVER_LOCATIONS, generate_api_key, generate_scoreboard_img
from bot.helpers.models import GuildModel, MatchModel
from bot.bot import G5Bot
from bot.helpers.errors import APIError, CustomError
from bot.resources import Config
from bot.views import VetoView, PickTeamsView, PollView
from bot.views.dropdownView import DropDownView


class MatchCog(commands.Cog, name="Match"):
    """"""

    def __init__(self, bot: G5Bot):
        self.bot = bot
        self.simulation_tasks = {}
        self.simulation_state = {}

    class PlaceholderUser:
        """Minimal discord-like user object used in simulation mode."""

        def __init__(self, user_id: int, display_name: str):
            self.id = user_id
            self.display_name = display_name
            self.mention = f"**{display_name}**"

        async def move_to(self, *_args, **_kwargs):
            return None

    def _build_simulated_match(self, match_id: str, map_name: str, connect_time: int, team1_name: str, team2_name: str, match_players: List[dict]) -> Match:
        match_data = {
            'id': match_id,
            'game_server_id': 'simulation',
            'team1': {
                'name': team1_name,
                'stats': {'score': 0}
            },
            'team2': {
                'name': team2_name,
                'stats': {'score': 0}
            },
            'settings': {
                'map': map_name,
                'connect_time': connect_time,
            },
            'finished': False,
            'rounds_played': 0,
            'players': match_players,
        }
        return Match.from_dict(match_data)

    def _build_simulated_round_match(self, match_id: str) -> Match:
        state = self.simulation_state.get(match_id)
        if not state:
            return None

        players = []
        for player in state['players']:
            player_stats = {
                'steam_id_64': str(player['steam_id']),
                'team': player['team'],
                'stats': {
                    'kills': player['kills'],
                    'deaths': player['deaths'],
                    'assists': player['assists'],
                    'kills_with_headshot': player['headshots'],
                    'mvps': player['mvps'],
                    '2ks': player['k2'],
                    '3ks': player['k3'],
                    '4ks': player['k4'],
                    '5ks': player['k5'],
                    'score': player['score'],
                }
            }
            players.append(player_stats)

        return Match.from_dict({
            'id': match_id,
            'game_server_id': 'simulation',
            'team1': {
                'name': state['team1_name'],
                'stats': {'score': state['team1_score']}
            },
            'team2': {
                'name': state['team2_name'],
                'stats': {'score': state['team2_score']}
            },
            'settings': {
                'map': state['map_name'],
                'connect_time': state['connect_time'],
            },
            'finished': False,
            'rounds_played': state['rounds_played'],
            'players': players,
        })

    def _stop_simulation_task(self, match_id: str):
        task = self.simulation_tasks.pop(match_id, None)
        if task and not task.done():
            task.cancel()
        self.simulation_state.pop(match_id, None)

    async def process_round_update(self, match_model: MatchModel, match_api: Match):
        game_server = None
        message = None

        for player_stat in match_api.players:
            try:
                player_model = await self.bot.db.get_player_by_steam_id(player_stat.steam_id)
                if player_model:
                    await self.bot.db.update_player_stats(player_model.discord.id, match_api.id, player_stat.to_dict)
            except Exception as e:
                self.bot.logger.error(e, exc_info=1)

        try:
            message = await match_model.text_channel.fetch_message(match_model.message_id)
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)

        if match_model.game_server_id != 'simulation':
            try:
                game_server = await self.bot.api.get_game_server(match_api.game_server_id)
            except Exception as e:
                self.bot.logger.error(e, exc_info=1)

        if message:
            try:
                embed = self.embed_match_info(match_api, game_server)
                await message.edit(embed=embed)
            except Exception as e:
                self.bot.logger.error(e, exc_info=1)

    async def _run_simulation_rounds(self, match_id: str):
        for _ in range(10):
            try:
                await asyncio.sleep(8)
                success = await self.run_simulation_round(match_id)
                if not success:
                    return
            except asyncio.CancelledError:
                return
            except Exception as e:
                self.bot.logger.error(e, exc_info=1)

    async def run_simulation_round(self, match_id: str):
        try:
            state = self.simulation_state.get(match_id)
            if not state:
                return False

            match_model = await self.bot.db.get_match_by_id(match_id)
            if not match_model or match_model.game_server_id != 'simulation':
                self._stop_simulation_task(match_id)
                return False

            state['rounds_played'] += 1
            winning_team = 'team1' if randint(0, 1) == 0 else 'team2'
            if winning_team == 'team1':
                state['team1_score'] += 1
            else:
                state['team2_score'] += 1

            for player in state['players']:
                kills = randint(0, 3)
                deaths = randint(0, 2)
                assists = randint(0, 2)
                player['kills'] += kills
                player['deaths'] += deaths
                player['assists'] += assists
                player['headshots'] += randint(0, kills)
                player['mvps'] += 1 if player['team'] == winning_team and kills > 0 and randint(0, 1) == 1 else 0
                player['k2'] += 1 if kills >= 2 else 0
                player['k3'] += 1 if kills >= 3 else 0
                player['k4'] += 1 if kills >= 4 else 0
                player['k5'] += 1 if kills >= 5 else 0
                player['score'] += kills * 2 + assists

            simulated_match = self._build_simulated_round_match(match_id)
            if simulated_match:
                await self.process_round_update(match_model, simulated_match)
                return True

            return False
        except asyncio.CancelledError:
            return False
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)
            return False

    @app_commands.command(name="sim-round", description="Trigger one fake round-end update for a simulation match")
    @app_commands.describe(match_id="Simulation match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def sim_round(self, interaction: Interaction, match_id: str):
        await interaction.response.defer(ephemeral=True)

        match_model = await self.bot.db.get_match_by_id(match_id)
        if not match_model:
            raise CustomError("Invalid match ID.")

        if match_model.game_server_id != 'simulation':
            raise CustomError("This command only works for simulation matches.")

        if match_id not in self.simulation_state:
            raise CustomError("Simulation state not found for this match.")

        updated = await self.run_simulation_round(match_id)
        if not updated:
            raise CustomError("Failed to generate simulation round update.")

        embed = Embed(description=f"Simulated round update sent for match #{match_id}.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="cancel-match", description="Cancel a live match")
    @app_commands.describe(match_id="Match ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def cancel_match(self, interaction: Interaction, match_id: str):
        """"""
        await interaction.response.defer()

        guild_model = await self.bot.db.get_guild_by_id(interaction.guild.id)
        match_model = await self.bot.db.get_match_by_id(match_id)
        if not match_model:
            raise CustomError("Invalid match ID.")

        self._stop_simulation_task(match_id)
        
        if match_model.game_server_id != 'simulation':
            try:
                await self.bot.api.cancel_match(match_id)
            except:
                pass

            try:
                await self.bot.api.stop_game_server(match_model.game_server_id)
            except:
                pass

            match_api = await self.bot.api.get_match(match_id)
        else:
            match_api = Match.from_dict({
                'id': match_model.id,
                'game_server_id': match_model.game_server_id,
                'team1': {
                    'name': match_model.team1_name,
                    'stats': {'score': match_model.team1_score}
                },
                'team2': {
                    'name': match_model.team2_name,
                    'stats': {'score': match_model.team2_score}
                },
                'settings': {
                    'map': match_model.map_name,
                    'connect_time': match_model.connect_time,
                },
                'cancel_reason': 'simulation_cancel',
                'finished': True,
                'rounds_played': match_model.rounds_played,
                'players': []
            })

        await self.finalize_match(match_model, match_api, guild_model)

        embed = Embed(description=f"Match #{match_id} cancelled successfully.")
        await interaction.followup.send(embed=embed)

        try:
            match_msg = await match_model.text_channel.fetch_message(match_model.message_id)
            await match_msg.delete()
        except:
            pass

    @app_commands.command(name="add-player", description="Add a player to a specific live match.")
    @app_commands.describe(user="A user to join the match")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_match_player(self, interaction: Interaction, user: Member, match_id: str, team: Literal["team1", "team2", "spectator"]):
        """"""
        await interaction.response.defer()

        match_model = await self.bot.db.get_match_by_id(match_id)
        if not match_model:
            raise CustomError("Invalid match ID.")
        
        if match_model.finished:
            raise CustomError("Match is already finished.")
        
        player_model = await self.bot.db.get_player_by_discord_id(user.id)
        if not player_model:
            raise CustomError(f"User {user.mention} is not linked.")
        
        await self.bot.api.add_match_player(match_id, player_model.steam_id, team)

        players_stats = [{
            'match_id': match_id,
            'steam_id': player_model.steam_id,
            'user_id': user.id,
            'team': team
        }]
        await self.bot.db.insert_players_stats(players_stats)

        team_channel = None
        if team == "team1":
            team_channel = match_model.team1_channel
        elif team == "team2":
            team_channel = match_model.team2_channel
        
        if team_channel:
            try:
                await team_channel.set_permissions(user, connect=True)
                await user.move_to(team_channel)
            except: pass

        embed = Embed(description=f"User {user.mention} added into match #{match_id}.")
        await interaction.followup.send(embed=embed)
        
    async def pick_teams(self, message: Message, users: List[Member], captain_method: str):
        """"""
        teams_view = PickTeamsView(self.bot, message, users)
        await teams_view.start(captain_method)
        await message.edit(embed=teams_view.embed_teams_pick("Start teams pickings"), view=teams_view)
        await teams_view.wait()
        if teams_view.users_left:
            raise asyncio.TimeoutError
        return teams_view.teams[0], teams_view.teams[1]
    
    async def autobalance_teams(self, users: List[Member]):
        """"""
        players_stats = await self.bot.db.get_players_stats([u.id for u in users])

        # Create a dictionary mapping PlayerStatsModel objects to discord.Member objects
        stats_dict = {ps: users[idx] for idx, ps in enumerate(players_stats)}
        
        # Sort players by their rating
        players_stats.sort(key=lambda x: x.rating, reverse=True)

        # Balance teams based on player ratings
        team_size = len(players_stats) // 2
        team_one, team_two = [], []

        # Distribute players to teams ensuring balanced total ratings
        for player in players_stats:
            team_one_rating = sum(p.rating for p in team_one)
            team_two_rating = sum(p.rating for p in team_two)
            
            if len(team_one) < team_size and (len(team_two) == team_size or team_one_rating <= team_two_rating):
                team_one.append(player)
            else:
                team_two.append(player)

        return list(map(stats_dict.get, team_one)), list(map(stats_dict.get, team_two))

    def randomize_teams(self, users: List[Member]):
        """"""
        temp_users = users.copy()
        shuffle(temp_users)
        team_size = len(temp_users) // 2
        team1_users = temp_users[:team_size]
        team2_users = temp_users[team_size:]
        return team1_users, team2_users
    
    def embed_match_info(
        self,
        match_stats: Match,
        game_server=None,
    ):
        """"""
        title = f"**{match_stats.team1_name}**  [ {match_stats.team1_score} : {match_stats.team2_score} ]  **{match_stats.team2_name}**"
        description = ''

        if game_server:
            description += f'📌 **Server:** `connect {game_server.ip}:{game_server.port}`\n' \
                           f'⚙️ **Game mode:** {game_server.game_mode}\n'

        description += f'🗺️ **Map:** {match_stats.map_name}\n\n'
        embed = Embed(title=title, description=description)

        author_name = f"🟢 Match #{match_stats.id}"
        embed.set_author(name=author_name)

        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        embed.set_footer(
            text= "🔸You'll be put on a random team when joining the server.\n" \
                  "🔸Once the match starts you'll be moved to your correct team.\n" \
                 f"🔸Match will be cancelled if any player doesn't join the server within {match_stats.connect_time} seconds.\n")

        return embed

    async def start_match(
        self,
        guild: Guild,
        message: Message,
        channel: VoiceChannel,
        queue_users: List[Member]=[], 
        team_method: str='captains',
        map_method: str='veto',
        captain_method: str='random',
        game_mode: str='competitive',
        connect_time: int=300,
    ):
        """"""
        await asyncio.sleep(3)
        simulation_mode = len(queue_users) == 1
        simulated_match = None

        try:
            if simulation_mode:
                placeholder = self.PlaceholderUser(
                    user_id=9_000_000_000_000_000 + int(time.time()) % 1_000_000,
                    display_name="Test Bot"
                )
                team1_users = [queue_users[0]]
                team2_users = [placeholder]
            elif team_method == 'captains' and len(queue_users) >= 4:
                team1_users, team2_users = await self.pick_teams(message, queue_users, captain_method)
            elif team_method == 'autobalance' and len(queue_users) >= 4:
                team1_users, team2_users = await self.autobalance_teams(queue_users)
            else:
                team1_users, team2_users = self.randomize_teams(queue_users)
            
            team1_players_model = await self.bot.db.get_players(team1_users)
            team2_players_model = await self.bot.db.get_players(team2_users)
            team1_captain = team1_users[0]
            team2_captain = team2_users[0]
            team1_name = team1_captain.display_name
            team2_name = team2_captain.display_name

            match_players = [ {
                'steam_id_64': str(player.steam_id),
                'team': 'team1' if player in team1_players_model else 'team2',
                'nickname_override': player.discord.display_name[:32]
            } for player in team1_players_model + team2_players_model]

            mpool = list(Config.maps.keys())
            if simulation_mode:
                map_name = choice(mpool)
                api_key = generate_api_key()
                sim_match_id = f"sim-{int(time.time())}-{guild.id % 1_000_000}"
                api_match = self._build_simulated_match(
                    sim_match_id,
                    map_name,
                    connect_time,
                    team1_name,
                    team2_name,
                    match_players
                )
                game_server = None
            else:
                if map_method == 'veto':
                    veto_view = VetoView(message, mpool, team1_captain, team2_captain)
                    await message.edit(embed=veto_view.embed_veto(), view=veto_view)
                    await veto_view.wait()
                    map_name = veto_view.maps_left[0]
                elif map_method == 'poll':
                    poll_view = PollView(message, mpool, queue_users)
                    map_name = await poll_view.start()
                else:
                    map_name = choice(mpool)

                placeholder = "Choose your game server location"
                options = [SelectOption(label=display_name, value=_id) for _id, display_name in GAME_SERVER_LOCATIONS.items()]
                dropdown = DropDownView([team1_captain, team2_captain], placeholder, options, 1, 1)
                await message.edit(embed=None, view=dropdown)
                await dropdown.wait()

                if any(x is None for x in dropdown.users_selections.values()):
                    raise asyncio.TimeoutError
                location = choice(list(dropdown.users_selections.values()))

                await message.edit(embed=Embed(description='Searching for available game servers...'), view=None)
                await asyncio.sleep(2)

                game_server = await self.fetch_game_server(location, game_mode)

                await message.edit(embed=Embed(description='Setting up match on game server...'), view=None)
                await asyncio.sleep(2)

                spectators = await self.bot.db.get_spectators(guild)
                for spec in spectators:
                    if spec.discord not in team1_users and spec.discord not in team2_users:
                        match_players.append({'steam_id_64': spec.steam_id, 'team': 'spectator'})

                api_key = generate_api_key()
                api_match = await self.bot.api.create_match(
                    game_server.id,
                    map_name,
                    team1_name,
                    team2_name,
                    match_players,
                    connect_time,
                    api_key
                )

                attempts = 0
                game_server = await self.bot.api.get_game_server(game_server.id)
                while not game_server.ip and attempts < 5:
                    game_server = await self.bot.api.get_game_server(game_server.id)
                    await asyncio.sleep(3)
                    attempts += 1
                
                if not game_server.ip:
                    raise(APIError("Something went wrong on game server."))

            await message.edit(embed=Embed(description='Setting up teams channels...'), view=None)
            team1_voice_users = [user for user in team1_users if isinstance(user, Member)]
            team2_voice_users = [user for user in team2_users if isinstance(user, Member)]
            category, team1_channel, team2_channel = await self.create_match_channels(
                api_match.id,
                team1_voice_users,
                team2_voice_users,
                guild
            )

            await self.bot.db.insert_match({
                'id': api_match.id,
                'game_server_id': game_server.id if game_server else 'simulation',
                'guild': guild.id,
                'channel': channel.id,
                'message': message.id,
                'category': category.id,
                'team1_channel': team1_channel.id,
                'team2_channel': team2_channel.id,
                'team1_name': team1_name,
                'team2_name': team2_name,
                'map_name': map_name,
                'api_key': api_key,
                'connect_time': api_match.connect_time
            })

            players_stats = []
            for u in team1_players_model + team2_players_model:
                players_stats.append({'match_id': api_match.id,
                                      'steam_id': u.steam_id,
                                      'user_id': u.discord.id,
                                      'team': 'team1' if u.discord in team1_users else 'team2'})
            await self.bot.db.insert_players_stats(players_stats)

            if simulation_mode:
                simulated_match = api_match
                self.simulation_state[api_match.id] = {
                    'team1_name': team1_name,
                    'team2_name': team2_name,
                    'team1_score': 0,
                    'team2_score': 0,
                    'rounds_played': 0,
                    'map_name': map_name,
                    'connect_time': connect_time,
                    'players': [
                        {
                            'steam_id': player.steam_id,
                            'team': 'team1' if player.discord in team1_users else 'team2',
                            'kills': 0,
                            'deaths': 0,
                            'assists': 0,
                            'headshots': 0,
                            'mvps': 0,
                            'k2': 0,
                            'k3': 0,
                            'k4': 0,
                            'k5': 0,
                            'score': 0,
                        }
                        for player in team1_players_model + team2_players_model
                    ]
                }
                self.simulation_tasks[api_match.id] = asyncio.create_task(self._run_simulation_rounds(api_match.id))

        except APIError as e:
            description = e.message
        except asyncio.TimeoutError:
            description = 'Setup took too long!'
        except ValueError as e:
            description = e
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)
            description = 'Something went wrong! See logs for details'
        else:
            embed = self.embed_match_info(simulated_match if simulated_match else api_match, game_server)
            await message.edit(embed=embed)

            return True

        embed = Embed(title="Match Setup Failed",
                      description=description, color=0xE02B2B)
        try:
            await message.edit(embed=embed, view=None)
        except:
            pass

    async def fetch_game_server(self, location, game_mode):
        """"""
        game_servers = await self.bot.api.get_game_servers()

        for game_server in game_servers:
            if game_server.booting:
                continue
            if not game_server.match_id:
                await self.bot.api.update_game_server(
                    game_server.id,
                    game_mode=game_mode,
                    location=location)
                return game_server

        raise ValueError("No game server available at the moment.")

    async def create_match_channels(
        self,
        match_id: int,
        team1_users: List[Member],
        team2_users: List[Member],
        guild: Guild
    ):
        """"""
        match_catg = await guild.create_category_channel(f"Match #{match_id}")
        team1_overwrites = {u: PermissionOverwrite(connect=True) for u in team1_users}
        team1_overwrites[guild.self_role] = PermissionOverwrite(connect=True)
        team1_overwrites[guild.default_role] = PermissionOverwrite(connect=False)
        team2_overwrites = {u: PermissionOverwrite(connect=True) for u in team2_users}
        team2_overwrites[guild.self_role] = PermissionOverwrite(connect=True)
        team2_overwrites[guild.default_role] = PermissionOverwrite(connect=False)

        team1_channel = await guild.create_voice_channel(
            name=f"Team 1",
            category=match_catg,
            overwrites=team1_overwrites
        )
    
        team2_channel = await guild.create_voice_channel(
            name=f"Team 2",
            category=match_catg,
            overwrites=team2_overwrites
        )

        awaitables = []
        for user in team1_users:
            awaitables.append(user.move_to(team1_channel))
        for user in team2_users:
            awaitables.append(user.move_to(team2_channel))
        await asyncio.gather(*awaitables, return_exceptions=True)

        return match_catg, team1_channel, team2_channel

    async def finalize_match(self, match_model: MatchModel, match_api: Match, guild_model: GuildModel):
        """"""
        self._stop_simulation_task(match_model.id)

        try:
            move_aws = [user.move_to(guild_model.waiting_channel)
                        for user in match_model.team1_channel.members + match_model.team2_channel.members]
            await asyncio.gather(*move_aws, return_exceptions=True)
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)
        
        team_channels = [
            match_model.team2_channel,
            match_model.team1_channel,
            match_model.category
        ]

        for channel in team_channels:
            try:
                await channel.delete()
            except Exception as e:
                self.bot.logger.error(e, exc_info=1)

        try:
            message = await match_model.text_channel.fetch_message(match_model.message_id)
            await message.delete()
        except Exception as e:
            self.bot.logger.error(e, exc_info=1)

        dict_stats = match_api.to_dict
        dict_stats.pop('players')
        
        await self.bot.db.update_match(match_api.id, **dict_stats)

        if not match_api.canceled:
            team1_steam_ids = [ps.steam_id for ps in match_api.players if ps.team == 'team1']
            team2_steam_ids = [ps.steam_id for ps in match_api.players if ps.team == 'team2']
            team1_players_model = await self.bot.db.get_players_by_steam_ids(team1_steam_ids)
            team2_players_model = await self.bot.db.get_players_by_steam_ids(team2_steam_ids)

            team1_stats = {
                player_model: next(player_stat for player_stat in match_api.players if player_model.steam_id == player_stat.steam_id)
                for player_model in team1_players_model
            }
            team2_stats = {
                player_model: next(player_stat for player_stat in match_api.players if player_model.steam_id == player_stat.steam_id)
                for player_model in team2_players_model
            }
            file = generate_scoreboard_img(match_api, team1_stats, team2_stats)
            await guild_model.results_channel.send(file=file)


async def setup(bot):
    await bot.add_cog(MatchCog(bot))
