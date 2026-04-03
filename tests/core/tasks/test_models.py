from datetime import datetime, timezone

from merlin.core.tasks.models import Task, TaskStatus, WorkerInfo


class TestTaskModel:
    def test_defaults(self) -> None:
        task = Task(
            asset="AAPL",
            source="yahoo",
            data_type="ohlcv",
            from_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )
        assert task.status == TaskStatus.PENDING
        assert task.retries == 0
        assert task.max_retries == 3
        assert task.worker_id is None
        assert task.error is None
        assert task.id is not None

    def test_status_values(self) -> None:
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.DEAD == "dead"


class TestWorkerInfo:
    def test_defaults(self) -> None:
        worker = WorkerInfo(hostname="test-host")
        assert worker.hostname == "test-host"
        assert worker.id is not None
        assert worker.started_at is not None
        assert worker.last_heartbeat is not None
