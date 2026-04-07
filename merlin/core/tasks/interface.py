from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Protocol
from uuid import UUID

from pydantic import BaseModel

from merlin.core.tasks.models import Task, TaskContext, TaskStatus, WorkerInfo


class TaskRepository(Protocol):
    async def create(self, task: Task) -> bool:
        """Create a task. Returns False if a duplicate exists (same key)."""
        ...

    async def claim(self, worker_id: UUID, group: str) -> Task | None:
        """Claim the next pending task for a worker in the given group."""
        ...

    async def update_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        *,
        error: str | None = None,
        retries: int | None = None,
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


class TaskExecutor[T](ABC):
    """Base class for task executors with typed params."""

    @abstractmethod
    def parse_params(self, raw: dict[str, Any]) -> T: ...

    @abstractmethod
    async def execute(self, ctx: TaskContext, params: T) -> None: ...


class ModelTaskExecutor[T: BaseModel](TaskExecutor[T], ABC):
    """Task executor with Pydantic model-based param parsing.

    Subclasses must set _params_type to their concrete params class:

        class MyExecutor(ModelTaskExecutor[MyParams]):
            _params_type = MyParams

            async def execute(self, ctx: TaskContext, params: MyParams) -> None: ...
    """

    _params_type: ClassVar[type[BaseModel]]

    def parse_params(self, raw: dict[str, Any]) -> T:
        return self._params_type.model_validate(raw)  # type: ignore[return-value]

    @abstractmethod
    async def execute(self, ctx: TaskContext, params: T) -> None: ...


class TaskSchedule(Protocol):
    """A schedule that generates tasks on a cron or interval basis."""

    @property
    def schedule(self) -> str:
        """Cron expression or interval (e.g. '@daily', 'every 4h', '0 6 * * *')."""
        ...

    async def generate_tasks(self) -> list[Task]: ...
