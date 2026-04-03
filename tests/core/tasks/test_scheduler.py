from __future__ import annotations

from datetime import datetime, timezone

from merlin.core.events.memory import InMemoryEventLog
from merlin.core.tasks.memory import InMemoryTaskRepository
from merlin.core.tasks.models import Task, TaskStatus
from merlin.core.tasks.scheduler import Scheduler


class FakeScheduleSource:
    def __init__(self, tasks: list[Task]) -> None:
        self.tasks = tasks

    async def generate_tasks(self) -> list[Task]:
        return self.tasks


def _make_task(asset: str = "AAPL") -> Task:
    return Task(
        asset=asset,
        source="yahoo",
        data_type="ohlcv",
        from_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        to_date=datetime(2025, 1, 31, tzinfo=timezone.utc),
    )


class TestScheduler:
    async def test_tick_creates_tasks(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        source = FakeScheduleSource([_make_task("AAPL"), _make_task("MSFT")])
        scheduler = Scheduler(repo, event_log, [source])

        created = await scheduler.tick()

        assert created == 2
        pending = await repo.find_by_status(TaskStatus.PENDING)
        assert len(pending) == 2

    async def test_tick_skips_duplicates(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        task = _make_task()
        source = FakeScheduleSource([task])
        scheduler = Scheduler(repo, event_log, [source])

        await scheduler.tick()
        # Same task again — duplicate source/asset/data_type/from_date
        source.tasks = [_make_task()]
        created = await scheduler.tick()

        assert created == 0

    async def test_tick_emits_events(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        source = FakeScheduleSource([_make_task()])
        scheduler = Scheduler(repo, event_log, [source])

        await scheduler.tick()

        events = await event_log.query()
        assert len(events) == 1
        assert events[0].action == "task_created"

    async def test_tick_multiple_sources(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        s1 = FakeScheduleSource([_make_task("AAPL")])
        s2 = FakeScheduleSource([_make_task("MSFT")])
        scheduler = Scheduler(repo, event_log, [s1, s2])

        created = await scheduler.tick()
        assert created == 2
