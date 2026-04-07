from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from merlin.app.market.bootstrap import setup_market_worker
from merlin.core.events.pg import PgEventLog
from merlin.core.tasks.pg_repository import PgTaskRepository
from merlin.core.tasks.worker import Worker
from merlin.services._bootstrap import bootstrap

logger = logging.getLogger(__name__)


async def run() -> None:
    config, db = await bootstrap(Path("config/default.yaml"))

    try:
        event_log = PgEventLog(db)
        executor, group = setup_market_worker(db)

        repo = PgTaskRepository(db)
        worker = Worker(
            repo,
            event_log,
            executor,
            group=group,
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
