from __future__ import annotations

from merlin.core.events.memory import InMemoryEventLog
from merlin.core.tasks.memory import InMemoryTaskRepository
from merlin.core.tasks.models import Task, TaskStatus
from merlin.core.tasks.scheduler import Scheduler


class FakeTaskSchedule:
    def __init__(self, tasks: list[Task]) -> None:
        self.tasks = tasks

    @property
    def schedule(self) -> str:
        return "@daily"

    async def generate_tasks(self) -> list[Task]:
        return self.tasks


def _make_task(key: str = "test:AAPL:ohlcv", group: str = "test") -> Task:
    return Task(key=key, group=group)


class TestScheduler:
    async def test_tick_creates_tasks(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        schedule = FakeTaskSchedule(
            [_make_task(key="test:AAPL:ohlcv"), _make_task(key="test:MSFT:ohlcv")]
        )
        scheduler = Scheduler(repo, event_log, [schedule])

        created = await scheduler.tick()

        assert created == 2
        pending = await repo.find_by_status(TaskStatus.PENDING)
        assert len(pending) == 2

    async def test_tick_skips_duplicates(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        task = _make_task()
        schedule = FakeTaskSchedule([task])
        scheduler = Scheduler(repo, event_log, [schedule])

        await scheduler.tick()
        # Same key again — duplicate
        schedule.tasks = [_make_task()]
        created = await scheduler.tick()

        assert created == 0

    async def test_tick_emits_events(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        schedule = FakeTaskSchedule([_make_task()])
        scheduler = Scheduler(repo, event_log, [schedule])

        await scheduler.tick()

        events = await event_log.query()
        assert len(events) == 1
        assert events[0].action == "task_created"

    async def test_tick_multiple_schedules(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        s1 = FakeTaskSchedule([_make_task(key="test:AAPL:ohlcv")])
        s2 = FakeTaskSchedule([_make_task(key="test:MSFT:ohlcv")])
        scheduler = Scheduler(repo, event_log, [s1, s2])

        created = await scheduler.tick()
        assert created == 2
