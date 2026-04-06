from merlin.core.tasks.models import Task, TaskContext, TaskStatus, WorkerInfo


class TestTaskModel:
    def test_defaults(self) -> None:
        task = Task(key="test:1", group="test")
        assert task.status == TaskStatus.PENDING
        assert task.retries == 0
        assert task.max_retries == 3
        assert task.worker_id is None
        assert task.error is None
        assert task.id is not None
        assert task.params == {}

    def test_with_params(self) -> None:
        task = Task(
            key="market:ingest:AAPL:ohlcv:2025-01-01",
            group="market.ingest",
            params={"asset": "AAPL", "source": "yahoo"},
        )
        assert task.params["asset"] == "AAPL"
        assert task.group == "market.ingest"

    def test_status_values(self) -> None:
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.DEAD == "dead"


class TestTaskContext:
    def test_create(self) -> None:
        task = Task(key="test:1", group="test")
        ctx = TaskContext(
            id=task.id,
            key=task.key,
            group=task.group,
            retries=task.retries,
            created_at=task.created_at,
        )
        assert ctx.id == task.id
        assert ctx.key == "test:1"
        assert ctx.group == "test"
        assert ctx.retries == 0


class TestWorkerInfo:
    def test_defaults(self) -> None:
        worker = WorkerInfo(hostname="test-host")
        assert worker.hostname == "test-host"
        assert worker.id is not None
        assert worker.started_at is not None
        assert worker.last_heartbeat is not None
