from __future__ import annotations

import logging

from merlin.core.db.interface import Database

logger = logging.getLogger(__name__)

MARKET_SCHEMA_VERSION = 2

MARKET_MIGRATIONS: list[str] = [
    # Version 1: assets table
    """
    CREATE TABLE IF NOT EXISTS assets (
        symbol TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        asset_type TEXT NOT NULL,
        exchange TEXT NOT NULL DEFAULT '',
        active BOOLEAN NOT NULL DEFAULT TRUE
    )
    """,
    # Version 2: market_ohlcv hypertable
    """
    CREATE TABLE IF NOT EXISTS market_ohlcv (
        symbol TEXT NOT NULL,
        market_date DATE NOT NULL,
        open DOUBLE PRECISION NOT NULL,
        high DOUBLE PRECISION NOT NULL,
        low DOUBLE PRECISION NOT NULL,
        close DOUBLE PRECISION NOT NULL,
        volume BIGINT NOT NULL,
        adjusted_close DOUBLE PRECISION,
        PRIMARY KEY (symbol, market_date)
    )
    """,
]


async def get_market_version(db: Database) -> int:
    try:
        rows = await db.fetch_all("SELECT version FROM market_schema_version")
    except Exception:
        return 0
    if not rows:
        return 0
    return max(int(row["version"]) for row in rows)


async def ensure_market_schema(db: Database) -> None:
    """Apply market-domain migrations."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS market_schema_version (
            version INTEGER NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    current = await get_market_version(db)
    logger.info("Market schema version: %d, target: %d", current, MARKET_SCHEMA_VERSION)

    for version in range(current + 1, MARKET_SCHEMA_VERSION + 1):
        if version <= len(MARKET_MIGRATIONS):
            logger.info("Applying market migration version %d", version)
            await db.execute(MARKET_MIGRATIONS[version - 1])
            await db.execute(
                "INSERT INTO market_schema_version (version) VALUES (:0)",
                [version],
            )
            logger.info("Applied market migration version %d", version)

    logger.info("Market schema is up to date at version %d", MARKET_SCHEMA_VERSION)
