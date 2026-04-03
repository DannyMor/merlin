from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from merlin.core.db.interface import Database

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

MIGRATIONS: list[str] = [
    # Version 1: schema_version table
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
]


async def get_current_version(db: Database) -> int:
    row = await db.fetch_one("SELECT MAX(version) as version FROM schema_version")
    if row is None:
        return 0
    version = row.get("version")
    if version is None:
        return 0
    return int(version)


async def ensure_schema(db: Database) -> None:
    """Apply any pending migrations to bring the database up to SCHEMA_VERSION."""
    # Always create schema_version table first
    await db.execute(MIGRATIONS[0])

    current = await get_current_version(db)
    logger.info("Current schema version: %d, target: %d", current, SCHEMA_VERSION)

    for version in range(current + 1, SCHEMA_VERSION + 1):
        if version <= len(MIGRATIONS):
            logger.info("Applying migration version %d", version)
            await db.execute(MIGRATIONS[version - 1])
            await db.execute(
                "INSERT INTO schema_version (version) VALUES (:0)",
                [version],
            )
            logger.info("Applied migration version %d", version)

    logger.info("Schema is up to date at version %d", SCHEMA_VERSION)
