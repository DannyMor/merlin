from __future__ import annotations

from datetime import datetime, timedelta, timezone

from merlin.core.tasks.memory import InMemoryTaskRepository
from merlin.core.tasks.models import Task, TaskStatus, WorkerInfo


def _make_task(
    asset: str = "AAPL",
    source: str = "yahoo",
    data_type: str = "ohlcv",
) -> Task:
    return Task(
        asset=asset,
        source=source,
        data_type=data_type,
        from_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        to_date=datetime(2025, 1, 31, tzinfo=timezone.utc),
    )


class TestInMemoryTaskRepository:
    async def test_create_and_get(self) -> None:
        repo = InMemoryTaskRepository()
        task = _make_task()
        assert await repo.create(task) is True

        result = await repo.get(task.id)
        assert result is not None
        assert result.asset == "AAPL"

    async def test_create_duplicate_rejected(self) -> None:
        repo = InMemoryTaskRepository()
        task1 = _make_task()
        task2 = _make_task()

        assert await repo.create(task1) is True
        assert await repo.create(task2) is False

    async def test_create_duplicate_allowed_after_completion(self) -> None:
        repo = InMemoryTaskRepository()
        task1 = _make_task()
        assert await repo.create(task1) is True
        await repo.update_status(task1.id, TaskStatus.COMPLETED)

        task2 = _make_task()
        assert await repo.create(task2) is True

    async def test_create_different_assets_allowed(self) -> None:
        repo = InMemoryTaskRepository()
        assert await repo.create(_make_task(asset="AAPL")) is True
        assert await repo.create(_make_task(asset="MSFT")) is True

    async def test_claim(self) -> None:
        repo = InMemoryTaskRepository()
        worker = WorkerInfo(hostname="test")
        await repo.register_worker(worker)

        task = _make_task()
        await repo.create(task)

        claimed = await repo.claim(worker.id)
        assert claimed is not None
        assert claimed.status == TaskStatus.RUNNING
        assert claimed.worker_id == worker.id
        assert claimed.started_at is not None

    async def test_claim_empty(self) -> None:
        repo = InMemoryTaskRepository()
        worker = WorkerInfo(hostname="test")
        result = await repo.claim(worker.id)
        assert result is None

    async def test_update_status(self) -> None:
        repo = InMemoryTaskRepository()
        task = _make_task()
        await repo.create(task)

        await repo.update_status(task.id, TaskStatus.COMPLETED)

        result = await repo.get(task.id)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED
        assert result.completed_at is not None

    async def test_update_status_with_error(self) -> None:
        repo = InMemoryTaskRepository()
        task = _make_task()
        await repo.create(task)

        await repo.update_status(task.id, TaskStatus.FAILED, error="boom")

        result = await repo.get(task.id)
        assert result is not None
        assert result.status == TaskStatus.FAILED
        assert result.error == "boom"

    async def test_find_by_status(self) -> None:
        repo = InMemoryTaskRepository()
        t1 = _make_task(asset="AAPL")
        t2 = _make_task(asset="MSFT")
        await repo.create(t1)
        await repo.create(t2)
        await repo.update_status(t1.id, TaskStatus.COMPLETED)

        pending = await repo.find_by_status(TaskStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].asset == "MSFT"

    async def test_find_stale_no_worker(self) -> None:
        repo = InMemoryTaskRepository()
        task = _make_task()
        await repo.create(task)
        worker = WorkerInfo(hostname="test")
        claimed = await repo.claim(worker.id)
        assert claimed is not None

        # Worker not registered, so task is stale
        stale = await repo.find_stale(0.0)
        assert len(stale) == 1

    async def test_find_stale_with_dead_worker(self) -> None:
        repo = InMemoryTaskRepository()
        worker = WorkerInfo(hostname="test")
        worker.last_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=5)
        await repo.register_worker(worker)

        task = _make_task()
        await repo.create(task)
        await repo.claim(worker.id)

        stale = await repo.find_stale(60.0)
        assert len(stale) == 1

    async def test_heartbeat(self) -> None:
        repo = InMemoryTaskRepository()
        worker = WorkerInfo(hostname="test")
        worker.last_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=5)
        await repo.register_worker(worker)

        await repo.heartbeat(worker.id)

        dead = await repo.find_dead_workers(60.0)
        assert len(dead) == 0

    async def test_find_dead_workers(self) -> None:
        repo = InMemoryTaskRepository()
        worker = WorkerInfo(hostname="test")
        worker.last_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=5)
        await repo.register_worker(worker)

        dead = await repo.find_dead_workers(60.0)
        assert len(dead) == 1

    async def test_remove_worker(self) -> None:
        repo = InMemoryTaskRepository()
        worker = WorkerInfo(hostname="test")
        await repo.register_worker(worker)
        await repo.remove_worker(worker.id)

        dead = await repo.find_dead_workers(0.0)
        assert len(dead) == 0
