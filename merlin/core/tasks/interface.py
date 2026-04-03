from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from merlin.core.tasks.models import Task, TaskStatus, WorkerInfo


class TaskRepository(Protocol):
    async def create(self, task: Task) -> bool:
        """Create a task. Returns False if a duplicate exists."""
        ...

    async def claim(self, worker_id: UUID) -> Task | None:
        """Claim the next pending task for a worker. Returns None if no tasks available."""
        ...

    async def update_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        *,
        error: str | None = None,
    ) -> None: ...

    async def get(self, task_id: UUID) -> Task | None: ...

    async def find_by_status(self, status: TaskStatus) -> list[Task]: ...

    async def find_stale(self, threshold_seconds: float) -> list[Task]:
        """Find running tasks whose worker hasn't sent a heartbeat within threshold."""
        ...

    async def register_worker(self, worker: WorkerInfo) -> None: ...

    async def heartbeat(self, worker_id: UUID) -> None: ...

    async def find_dead_workers(self, threshold_seconds: float) -> list[WorkerInfo]: ...

    async def remove_worker(self, worker_id: UUID) -> None: ...


class TaskExecutor(Protocol):
    async def execute(self, task: Task) -> None: ...


class ScheduleSource(Protocol):
    async def generate_tasks(self) -> list[Task]: ...
