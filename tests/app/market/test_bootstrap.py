from __future__ import annotations

from pathlib import Path

from merlin.app.market.bootstrap import setup_market_schedules, setup_market_worker
from merlin.app.market.tasks.ingest import MarketIngestExecutor, MarketIngestSchedule
from merlin.core.db.memory import InMemoryDatabase


class TestBootstrap:
    async def test_setup_market_worker(self) -> None:
        db = InMemoryDatabase()
        await db.connect()

        executor, group = setup_market_worker(db)

        assert isinstance(executor, MarketIngestExecutor)
        assert group == "market.ingest"

    def test_setup_market_schedules(self) -> None:
        schedules = setup_market_schedules(Path("config/assets.yaml"))

        assert len(schedules) == 1
        assert isinstance(schedules[0], MarketIngestSchedule)

    async def test_setup_market_schedules_generates_tasks(self) -> None:
        schedules = setup_market_schedules(Path("config/assets.yaml"))

        tasks = await schedules[0].generate_tasks()

        # 7 assets * 3 data types = 21 tasks
        assert len(tasks) == 21
        assert all(t.group == "market.ingest" for t in tasks)
