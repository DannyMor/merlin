from __future__ import annotations

from datetime import datetime, timedelta, timezone

from merlin.core.events.memory import InMemoryEventLog
from merlin.core.events.models import EventLevel
from merlin.core.tasks.memory import InMemoryTaskRepository
from merlin.core.tasks.models import Task, TaskStatus, WorkerInfo
from merlin.core.tasks.reaper import Reaper


def _make_task(asset: str = "AAPL") -> Task:
    return Task(
        asset=asset,
        source="yahoo",
        data_type="ohlcv",
        from_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        to_date=datetime(2025, 1, 31, tzinfo=timezone.utc),
    )


def _dead_worker() -> WorkerInfo:
    worker = WorkerInfo(hostname="dead-host")
    worker.last_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=10)
    return worker


class TestReaper:
    async def test_tick_resets_stale_task(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        reaper = Reaper(repo, event_log, stale_threshold=60.0, max_retries=3)

        worker = _dead_worker()
        await repo.register_worker(worker)

        task = _make_task()
        await repo.create(task)
        await repo.claim(worker.id)

        reaped = await reaper.tick()

        assert reaped == 1
        result = await repo.get(task.id)
        assert result is not None
        assert result.status == TaskStatus.PENDING

    async def test_tick_marks_dead_after_max_retries(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        reaper = Reaper(repo, event_log, stale_threshold=60.0, max_retries=2)

        worker = _dead_worker()
        await repo.register_worker(worker)

        task = _make_task()
        task.retries = 2
        await repo.create(task)
        await repo.claim(worker.id)

        reaped = await reaper.tick()

        assert reaped == 1
        result = await repo.get(task.id)
        assert result is not None
        assert result.status == TaskStatus.DEAD

    async def test_tick_emits_reset_event(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        reaper = Reaper(repo, event_log, stale_threshold=60.0)

        worker = _dead_worker()
        await repo.register_worker(worker)

        task = _make_task()
        await repo.create(task)
        await repo.claim(worker.id)

        await reaper.tick()

        events = await event_log.query(level=EventLevel.WARN)
        actions = [e.action for e in events]
        assert "task_reset" in actions

    async def test_tick_emits_dead_event(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        reaper = Reaper(repo, event_log, stale_threshold=60.0, max_retries=0)

        worker = _dead_worker()
        await repo.register_worker(worker)

        task = _make_task()
        await repo.create(task)
        await repo.claim(worker.id)

        await reaper.tick()

        events = await event_log.query(level=EventLevel.ERROR)
        assert len(events) == 1
        assert events[0].action == "task_dead"

    async def test_tick_removes_dead_workers(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        reaper = Reaper(repo, event_log, stale_threshold=60.0)

        worker = _dead_worker()
        await repo.register_worker(worker)

        await reaper.tick()

        dead = await repo.find_dead_workers(60.0)
        assert len(dead) == 0

    async def test_tick_no_stale_tasks(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        reaper = Reaper(repo, event_log, stale_threshold=60.0)

        reaped = await reaper.tick()
        assert reaped == 0
