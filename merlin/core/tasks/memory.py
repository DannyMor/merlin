from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from merlin.core.tasks.models import TaskStatus

if TYPE_CHECKING:
    from uuid import UUID

    from merlin.core.tasks.models import Task, WorkerInfo


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._workers: dict[str, WorkerInfo] = {}

    async def create(self, task: Task) -> bool:
        for existing in self._tasks.values():
            if existing.key == task.key and existing.status in (
                TaskStatus.PENDING,
                TaskStatus.RUNNING,
            ):
                return False
        self._tasks[str(task.id)] = task
        return True

    async def claim(self, worker_id: UUID, group: str) -> Task | None:
        for task in self._tasks.values():
            if task.status == TaskStatus.PENDING and task.group == group:
                task.status = TaskStatus.RUNNING
                task.worker_id = worker_id
                task.started_at = datetime.now(timezone.utc)
                task.updated_at = datetime.now(timezone.utc)
                return task
        return None

    async def update_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        *,
        error: str | None = None,
    ) -> None:
        task = self._tasks.get(str(task_id))
        if task is None:
            return
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        if error is not None:
            task.error = error
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            task.completed_at = datetime.now(timezone.utc)

    async def get(self, task_id: UUID) -> Task | None:
        return self._tasks.get(str(task_id))

    async def find_by_status(self, status: TaskStatus) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == status]

    async def find_stale(self, threshold_seconds: float) -> list[Task]:
        now = datetime.now(timezone.utc)
        stale: list[Task] = []
        for task in self._tasks.values():
            if task.status != TaskStatus.RUNNING or task.worker_id is None:
                continue
            worker = self._workers.get(str(task.worker_id))
            if worker is None:
                stale.append(task)
                continue
            elapsed = (now - worker.last_heartbeat).total_seconds()
            if elapsed > threshold_seconds:
                stale.append(task)
        return stale

    async def register_worker(self, worker: WorkerInfo) -> None:
        self._workers[str(worker.id)] = worker

    async def heartbeat(self, worker_id: UUID) -> None:
        worker = self._workers.get(str(worker_id))
        if worker is not None:
            worker.last_heartbeat = datetime.now(timezone.utc)

    async def find_dead_workers(self, threshold_seconds: float) -> list[WorkerInfo]:
        now = datetime.now(timezone.utc)
        dead: list[WorkerInfo] = []
        for worker in self._workers.values():
            elapsed = (now - worker.last_heartbeat).total_seconds()
            if elapsed > threshold_seconds:
                dead.append(worker)
        return dead

    async def remove_worker(self, worker_id: UUID) -> None:
        self._workers.pop(str(worker_id), None)
