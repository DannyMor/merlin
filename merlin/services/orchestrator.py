from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

import yaml

from merlin.app.market.tasks.ingest import MarketScheduleSource
from merlin.core.config.loader import load_config
from merlin.core.db.timescaledb import TimescaleDB
from merlin.core.events.pg import PgEventLog
from merlin.core.sources.interface import DataType
from merlin.core.tasks.reaper import Reaper
from merlin.core.tasks.scheduler import Scheduler

logger = logging.getLogger(__name__)


def _load_asset_symbols(path: str = "config/assets.yaml") -> list[str]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return [str(asset["symbol"]) for asset in data.get("assets", [])]


async def run() -> None:
    config = load_config(Path("config/default.yaml"))

    logging.basicConfig(level=config.logging.level, format=config.logging.format)

    db = TimescaleDB(config.db)
    await db.connect()

    try:
        from merlin.core.db.migrations import ensure_schema

        await ensure_schema(db)

        event_log = PgEventLog(db)

        from merlin.core.tasks.pg_repository import PgTaskRepository

        repo = PgTaskRepository(db)

        assets = _load_asset_symbols()
        data_types = [DataType.OHLCV, DataType.DIVIDENDS, DataType.SPLITS]
        schedule_source = MarketScheduleSource(assets, data_types)

        scheduler = Scheduler(
            repo,
            event_log,
            [schedule_source],
            poll_interval=config.scheduler.poll_interval_seconds,
        )

        reaper = Reaper(
            repo,
            event_log,
            stale_threshold=config.reaper.stale_threshold_seconds,
            max_retries=config.reaper.max_retries,
            poll_interval=config.reaper.poll_interval_seconds,
        )

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: (scheduler.stop(), reaper.stop()))

        logger.info("Starting orchestrator (scheduler + reaper)")
        await asyncio.gather(scheduler.run(), reaper.run())
    finally:
        await db.disconnect()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
