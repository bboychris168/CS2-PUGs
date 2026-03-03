"""
Extend game_mode enum with additional CS2 game modes
"""

from yoyo import step

__depends__ = {'20211226_01_aVejE-create-base-tables'}

steps = [
    step("ALTER TYPE game_mode ADD VALUE IF NOT EXISTS 'casual';"),
    step("ALTER TYPE game_mode ADD VALUE IF NOT EXISTS 'arms_race';"),
    step("ALTER TYPE game_mode ADD VALUE IF NOT EXISTS 'ffa_deathmatch';"),
    step("ALTER TYPE game_mode ADD VALUE IF NOT EXISTS 'retakes';"),
    step("ALTER TYPE game_mode ADD VALUE IF NOT EXISTS 'custom';"),
]
