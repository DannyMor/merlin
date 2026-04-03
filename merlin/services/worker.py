from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from merlin.app.market.sources.yahoo import YahooFinanceSource
from merlin.app.market.tasks.ingest import MarketIngestExecutor
from merlin.core.config.loader import load_config
from merlin.core.db.timescaledb import TimescaleDB
from merlin.core.events.pg import PgEventLog
from merlin.core.tasks.worker import Worker

logger = logging.getLogger(__name__)


async def run() -> None:
    config = load_config(Path("config/default.yaml"))

    logging.basicConfig(level=config.logging.level, format=config.logging.format)

    db = TimescaleDB(config.db)
    await db.connect()

    try:
        from merlin.core.db.migrations import ensure_schema

        await ensure_schema(db)

        event_log = PgEventLog(db)
        source = YahooFinanceSource()
        executor = MarketIngestExecutor(source, db)

        from merlin.core.tasks.pg_repository import PgTaskRepository

        repo = PgTaskRepository(db)
        worker = Worker(
            repo,
            event_log,
            executor,
            poll_interval=config.worker.poll_interval_seconds,
            heartbeat_interval=config.worker.heartbeat_interval_seconds,
        )

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, worker.stop)

        logger.info("Starting worker")
        await worker.run()
    finally:
        await db.disconnect()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
