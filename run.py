# bot.py

import asyncio
import os
import json

from discord import Intents

from bot.resources import Config
from bot.bot import G5Bot


_CWD = os.path.dirname(os.path.abspath(__file__))
INTENTS_FILE = os.path.join(_CWD, 'intents.json')
with open(INTENTS_FILE) as f:
    intents_json = json.load(f)


def _normalize_intent_keys(raw_intents: dict) -> dict:
    aliases = {
        'emojis': 'emojis_and_stickers',
        'messages': 'guild_messages',
        'reactions': 'guild_reactions',
        'typing': 'guild_typing',
    }
    valid_flags = set(Intents.VALID_FLAGS)
    normalized = {}
    for key, value in raw_intents.items():
        mapped_key = aliases.get(key, key)
        if mapped_key in valid_flags:
            normalized[mapped_key] = bool(value)
    return normalized


intents = Intents(**_normalize_intent_keys(intents_json))
bot = G5Bot(intents=intents)


async def main():
    await bot.load_cogs()
    await bot.start(Config.token)


asyncio.run(main())
