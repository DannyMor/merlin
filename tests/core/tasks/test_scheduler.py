from __future__ import annotations

from merlin.core.events.memory import InMemoryEventLog
from merlin.core.tasks.memory import InMemoryTaskRepository
from merlin.core.tasks.models import TaskStatus
from merlin.core.tasks.scheduler import Scheduler
from tests.conftest import make_task
from tests.core.tasks.conftest import FakeTaskSchedule


class TestScheduler:
    async def test_tick_creates_tasks(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        schedule = FakeTaskSchedule(
            [make_task(key="test:AAPL:ohlcv"), make_task(key="test:MSFT:ohlcv")]
        )
        scheduler = Scheduler(repo, event_log, [schedule])

        created = await scheduler.tick()

        assert created == 2
        pending = await repo.find_by_status(TaskStatus.PENDING)
        assert len(pending) == 2

    async def test_tick_skips_duplicates(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        task = make_task()
        schedule = FakeTaskSchedule([task])
        scheduler = Scheduler(repo, event_log, [schedule])

        await scheduler.tick()
        schedule.tasks = [make_task()]
        created = await scheduler.tick()

        assert created == 0

    async def test_tick_emits_events(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        schedule = FakeTaskSchedule([make_task()])
        scheduler = Scheduler(repo, event_log, [schedule])

        await scheduler.tick()

        events = await event_log.query()
        assert len(events) == 1
        assert events[0].action == "task_created"

    async def test_tick_multiple_schedules(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        s1 = FakeTaskSchedule([make_task(key="test:AAPL:ohlcv")])
        s2 = FakeTaskSchedule([make_task(key="test:MSFT:ohlcv")])
        scheduler = Scheduler(repo, event_log, [s1, s2])

        created = await scheduler.tick()
        assert created == 2
