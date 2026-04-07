from __future__ import annotations

import logging
from pathlib import Path

from merlin.app.market.db.migrations import ensure_market_schema
from merlin.core.config.loader import load_config
from merlin.core.config.models import MerlinConfig
from merlin.core.db.migrations import ensure_schema
from merlin.core.db.timescaledb import TimescaleDB


async def bootstrap(config_path: Path) -> tuple[MerlinConfig, TimescaleDB]:
    """Shared service bootstrap: load config, connect DB, run migrations."""
    config = load_config(config_path)

    logging.basicConfig(level=config.logging.level, format=config.logging.format)

    db = TimescaleDB(config.db)
    await db.connect()

    await ensure_schema(db)
    await ensure_market_schema(db)

    return config, db
