from __future__ import annotations

import asyncio
from uuid import UUID

from merlin.core.events.memory import InMemoryEventLog
from merlin.core.events.models import EventLevel
from merlin.core.tasks.memory import InMemoryTaskRepository
from merlin.core.tasks.models import TaskStatus
from merlin.core.tasks.worker import Worker
from tests.conftest import make_task
from tests.core.tasks.conftest import FakeExecutor, FakeParams


class FailingHeartbeatRepo(InMemoryTaskRepository):
    """Repository where heartbeat always fails."""

    async def heartbeat(self, worker_id: UUID) -> None:
        raise ConnectionError("DB unavailable")


class TransientHeartbeatRepo(InMemoryTaskRepository):
    """Repository where the first heartbeat fails, then recovers."""

    def __init__(self) -> None:
        super().__init__()
        self._heartbeat_calls = 0

    async def heartbeat(self, worker_id: UUID) -> None:
        self._heartbeat_calls += 1
        if self._heartbeat_calls == 1:
            raise ConnectionError("Transient failure")
        await super().heartbeat(worker_id)


class TestWorker:
    async def test_tick_claims_and_executes(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()
        worker = Worker(repo, event_log, executor, group="test")

        task = make_task(params={"value": "hello"})
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

        task = make_task(params={"value": "hello"})
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

        await repo.create(make_task(params={"value": "hello"}))
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

        await repo.create(make_task(params={"value": "hello"}))
        await worker.tick()

        events = await event_log.query(level=EventLevel.ERROR)
        assert len(events) == 1
        assert events[0].action == "task_failed"

    async def test_tick_only_claims_from_own_group(self) -> None:
        repo = InMemoryTaskRepository()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()
        worker = Worker(repo, event_log, executor, group="other")

        await repo.create(make_task(group="test"))

        processed = await worker.tick()
        assert processed is False

    async def test_parse_params(self) -> None:
        executor = FakeExecutor()
        params = executor.parse_params({"value": "parsed"})
        assert isinstance(params, FakeParams)
        assert params.value == "parsed"

    async def test_self_terminates_on_heartbeat_failure(self) -> None:
        repo = FailingHeartbeatRepo()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()

        worker = Worker(
            repo,
            event_log,
            executor,
            group="test",
            poll_interval=0.01,
            heartbeat_interval=0.01,
            max_heartbeat_failures=2,
        )

        await worker.run()

        assert worker.liveness_failed is True

    async def test_heartbeat_recovers_from_transient_failure(self) -> None:
        repo = TransientHeartbeatRepo()
        event_log = InMemoryEventLog()
        executor = FakeExecutor()

        worker = Worker(
            repo,
            event_log,
            executor,
            group="test",
            poll_interval=0.01,
            heartbeat_interval=0.01,
            max_heartbeat_failures=3,
        )

        async def stop_after_delay() -> None:
            await asyncio.sleep(0.1)
            worker.stop()

        await asyncio.gather(worker.run(), stop_after_delay())

        assert worker.liveness_failed is False
