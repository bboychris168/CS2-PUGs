"""
Add poll value to map_method enum
"""

from yoyo import step

__depends__ = {'20211226_01_aVejE-create-base-tables'}

steps = [
    step(
        "ALTER TYPE map_method ADD VALUE IF NOT EXISTS 'poll';",
        # PostgreSQL does not support removing enum values; rollback is a no-op
    )
]
