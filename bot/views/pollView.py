# bot/views/pollView.py

import asyncio
import datetime
from random import choice
from typing import List

import discord

from bot.resources import Config


POLL_DURATION_SECS = 60  # seconds the vote actually runs before force-ending


class PollView:
    """Manages a Discord-native Poll for map selection.

    Discord enforces a minimum poll duration of 1 hour, so the poll is
    created with ``duration=timedelta(hours=1)`` and then force-ended via
    ``end_poll()`` after POLL_DURATION_SECS seconds. The native Discord UI
    already displays live vote tallies and a countdown for all players.
    """

    def __init__(
        self,
        message: discord.Message,
        mpool: List[str],
        players: List[discord.Member],
    ):
        """
        Parameters
        ----------
        message:
            The existing match-setup message; repurposed to show a countdown.
        mpool:
            List of map keys (e.g. ``["de_mirage", "de_nuke", ...]``).
        players:
            Players in the lobby (reserved for future mention use).
        """
        self.message = message
        self.mpool = mpool
        self.players = players

    async def start(self) -> str:
        """Send the poll, run the countdown, end the poll, and return the
        winning map key. Ties are broken by :func:`random.choice`."""
        channel = self.message.channel

        # Build the Discord Poll (1 hour minimum; we end it early)
        poll = discord.Poll(
            question="🗺️  Vote for the next map!",
            duration=datetime.timedelta(hours=1),
            allow_multiselect=False,
        )
        for map_key in self.mpool:
            poll.add_answer(text=Config.maps[map_key])

        # Post the poll
        poll_msg = await channel.send(poll=poll)

        # Live countdown — update the setup embed every 10 seconds
        remaining = POLL_DURATION_SECS
        while remaining > 0:
            embed = discord.Embed(
                description=(
                    "🗳️ **Map vote is live!**\n"
                    "React to the poll above to cast your vote.\n\n"
                    f"⏱️ Ends in **{remaining}s**"
                )
            )
            await self.message.edit(embed=embed, view=None)
            sleep_for = min(10, remaining)
            await asyncio.sleep(sleep_for)
            remaining -= sleep_for

        # Force-close the poll; the returned message has updated vote counts
        poll_msg = await poll_msg.end_poll()

        # Determine winner — ties broken randomly
        answers = poll_msg.poll.answers
        if not answers:
            # Fallback: pick a random map if something went wrong
            return choice(self.mpool)

        max_votes = max(a.vote_count for a in answers)
        winners = [a for a in answers if a.vote_count == max_votes]
        winning_answer = choice(winners)

        # Map display name back to its de_ key
        reverse_map = {display: key for key, display in Config.maps.items()}
        return reverse_map.get(winning_answer.media.text, choice(self.mpool))
