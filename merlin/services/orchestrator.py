from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from merlin.app.market.bootstrap import setup_market_schedules
from merlin.core.config.loader import load_config
from merlin.core.db.timescaledb import TimescaleDB
from merlin.core.events.pg import PgEventLog
from merlin.core.tasks.reaper import Reaper
from merlin.core.tasks.scheduler import Scheduler

logger = logging.getLogger(__name__)


async def run() -> None:
    config = load_config(Path("config/default.yaml"))

    logging.basicConfig(level=config.logging.level, format=config.logging.format)

    db = TimescaleDB(config.db)
    await db.connect()

    try:
        from merlin.app.market.db.migrations import ensure_market_schema
        from merlin.core.db.migrations import ensure_schema

        await ensure_schema(db)
        await ensure_market_schema(db)

        event_log = PgEventLog(db)

        from merlin.core.tasks.pg_repository import PgTaskRepository

        repo = PgTaskRepository(db)

        schedules = setup_market_schedules()

        scheduler = Scheduler(
            repo,
            event_log,
            schedules,
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
