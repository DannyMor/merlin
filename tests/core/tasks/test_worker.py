from __future__ import annotations

from datetime import datetime, timezone

from merlin.core.events.memory import InMemoryEventLog
from merlin.core.events.models import EventLevel
from merlin.core.tasks.memory import InMemoryTaskRepository
from merlin.core.tasks.models import Task, TaskStatus
from merlin.core.tasks.worker import Worker


class FakeExecutor:
    def __init__(self, *, fail: bool = False) -> None:
        self.executed: list[Task] = []
        self._fail = fail

    async def execute(self, task: Task) -> None:
        self.executed.append(task)
        if self._fail:
            msg = "Simulated failure"
            raise RuntimeError(msg)


def _make_task(asset: str = "AAPL") -> Task:
    return Task(
        asset=asset,
        source="yahoo",
        data_type="ohlcv",
        from_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        to_date=datetime(2025, 1, 31, tzinfo=timezone.utc),
    )


class TestWorker:
    async def test_tick_claims_and_executes(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()
        worker = Worker(repo, event_log, executor)

        task = _make_task()
        await repo.create(task)

        processed = await worker.tick()

        assert processed is True
        assert len(executor.executed) == 1
        result = await repo.get(task.id)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED

    async def test_tick_no_tasks(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()
        worker = Worker(repo, event_log, executor)

        processed = await worker.tick()
        assert processed is False

    async def test_tick_handles_failure(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor(fail=True)
        worker = Worker(repo, event_log, executor)

        task = _make_task()
        await repo.create(task)

        processed = await worker.tick()

        assert processed is True
        result = await repo.get(task.id)
        assert result is not None
        assert result.status == TaskStatus.FAILED
        assert result.error == "Simulated failure"

    async def test_tick_emits_events_on_success(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()
        worker = Worker(repo, event_log, executor)

        await repo.create(_make_task())
        await worker.tick()

        events = await event_log.query()
        actions = [e.action for e in events]
        assert "task_started" in actions
        assert "task_completed" in actions

    async def test_tick_emits_error_event_on_failure(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor(fail=True)
        worker = Worker(repo, event_log, executor)

        await repo.create(_make_task())
        await worker.tick()

        events = await event_log.query(level=EventLevel.ERROR)
        assert len(events) == 1
        assert events[0].action == "task_failed"
