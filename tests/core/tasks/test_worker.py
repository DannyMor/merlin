from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pydantic import BaseModel

from merlin.core.events.memory import InMemoryEventLog
from merlin.core.events.models import EventLevel
from merlin.core.tasks.interface import TaskExecutor
from merlin.core.tasks.memory import InMemoryTaskRepository
from merlin.core.tasks.models import Task, TaskContext, TaskStatus
from merlin.core.tasks.worker import Worker

if TYPE_CHECKING:
    from uuid import UUID


class FakeParams(BaseModel):
    value: str = "test"


class FakeExecutor(TaskExecutor[FakeParams]):
    def __init__(self, *, fail: bool = False) -> None:
        self.executed: list[tuple[TaskContext, FakeParams]] = []
        self._fail = fail

    async def execute(self, ctx: TaskContext, params: FakeParams) -> None:
        self.executed.append((ctx, params))
        if self._fail:
            msg = "Simulated failure"
            raise RuntimeError(msg)


def _make_task(key: str = "test:1", group: str = "test") -> Task:
    return Task(key=key, group=group, params={"value": "hello"})


class TestWorker:
    async def test_tick_claims_and_executes(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()
        worker = Worker(repo, event_log, executor, group="test")

        task = _make_task()
        await repo.create(task)

        processed = await worker.tick()

        assert processed is True
        assert len(executor.executed) == 1
        ctx, params = executor.executed[0]
        assert ctx.key == "test:1"
        assert params.value == "hello"
        result = await repo.get(task.id)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED

    async def test_tick_no_tasks(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()
        worker = Worker(repo, event_log, executor, group="test")

        processed = await worker.tick()
        assert processed is False

    async def test_tick_handles_failure(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor(fail=True)
        worker = Worker(repo, event_log, executor, group="test")

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
        worker = Worker(repo, event_log, executor, group="test")

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
        worker = Worker(repo, event_log, executor, group="test")

        await repo.create(_make_task())
        await worker.tick()

        events = await event_log.query(level=EventLevel.ERROR)
        assert len(events) == 1
        assert events[0].action == "task_failed"

    async def test_tick_only_claims_from_own_group(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()
        worker = Worker(repo, event_log, executor, group="other")

        await repo.create(_make_task(group="test"))

        processed = await worker.tick()
        assert processed is False

    async def test_parse_params_auto_extraction(self) -> None:
        executor = FakeExecutor()
        params = executor.parse_params({"value": "parsed"})
        assert isinstance(params, FakeParams)
        assert params.value == "parsed"

    async def test_self_terminates_on_heartbeat_failure(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()

        # Override heartbeat to always fail
        async def failing_heartbeat(worker_id: UUID) -> None:
            raise ConnectionError("DB unavailable")

        repo.heartbeat = failing_heartbeat  # type: ignore[assignment]

        worker = Worker(
            repo,
            event_log,
            executor,
            group="test",
            poll_interval=0.01,
            heartbeat_interval=0.01,
            max_heartbeat_failures=2,
        )

        # run() should exit because heartbeat failures trigger self-termination
        await worker.run()

        assert worker.liveness_failed is True

    async def test_heartbeat_recovers_from_transient_failure(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()

        call_count = 0
        original_heartbeat = repo.heartbeat

        async def sometimes_failing_heartbeat(worker_id: UUID) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Transient failure")
            await original_heartbeat(worker_id)

        repo.heartbeat = sometimes_failing_heartbeat  # type: ignore[assignment]

        worker = Worker(
            repo,
            event_log,
            executor,
            group="test",
            poll_interval=0.01,
            heartbeat_interval=0.01,
            max_heartbeat_failures=3,
        )

        # Run briefly — should not self-terminate since failure is transient
        async def stop_after_delay() -> None:
            await asyncio.sleep(0.1)
            worker.stop()

        await asyncio.gather(worker.run(), stop_after_delay())

        assert worker.liveness_failed is False
