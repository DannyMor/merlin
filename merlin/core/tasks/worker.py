from __future__ import annotations

import asyncio
import logging
import platform
from typing import TYPE_CHECKING, Any

from merlin.core.events.models import Event, EventLevel, EventSource
from merlin.core.tasks.models import TaskContext, TaskStatus, WorkerInfo

if TYPE_CHECKING:
    from merlin.core.events.interface import EventLog
    from merlin.core.tasks.interface import TaskExecutor, TaskRepository

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        repository: TaskRepository,
        event_log: EventLog,
        executor: TaskExecutor[Any],
        group: str,
        poll_interval: float = 5.0,
        heartbeat_interval: float = 15.0,
    ) -> None:
        self._repo = repository
        self._event_log = event_log
        self._executor = executor
        self._group = group
        self._poll_interval = poll_interval
        self._heartbeat_interval = heartbeat_interval
        self._info = WorkerInfo(hostname=platform.node())
        self._running = False

    @property
    def worker_id(self) -> WorkerInfo:
        return self._info

    async def _heartbeat_loop(self) -> None:
        while self._running:
            await self._repo.heartbeat(self._info.id)
            await asyncio.sleep(self._heartbeat_interval)

    async def tick(self) -> bool:
        """Try to claim and execute one task. Returns True if a task was processed."""
        task = await self._repo.claim(self._info.id, self._group)
        if task is None:
            return False

        ctx = TaskContext(
            id=task.id,
            key=task.key,
            group=task.group,
            retries=task.retries,
            created_at=task.created_at,
        )

        await self._event_log.emit(
            Event(
                source=EventSource.WORKER,
                level=EventLevel.INFO,
                component="worker",
                action="task_started",
                detail={"task_id": str(task.id), "key": task.key},
            )
        )

        try:
            params = self._executor.parse_params(task.params)
            await self._executor.execute(ctx, params)
            await self._repo.update_status(task.id, TaskStatus.COMPLETED)
            await self._event_log.emit(
                Event(
                    source=EventSource.WORKER,
                    level=EventLevel.INFO,
                    component="worker",
                    action="task_completed",
                    detail={"task_id": str(task.id), "key": task.key},
                )
            )
        except Exception as exc:
            error_msg = str(exc)
            await self._repo.update_status(task.id, TaskStatus.FAILED, error=error_msg)
            await self._event_log.emit(
                Event(
                    source=EventSource.WORKER,
                    level=EventLevel.ERROR,
                    component="worker",
                    action="task_failed",
                    detail={
                        "task_id": str(task.id),
                        "key": task.key,
                        "error": error_msg,
                    },
                )
            )
            logger.exception("Task %s failed", task.id)

        return True

    async def run(self) -> None:
        self._running = True
        await self._repo.register_worker(self._info)
        logger.info("Worker %s starting (group=%s)", self._info.id, self._group)

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        try:
            while self._running:
                processed = await self.tick()
                if not processed:
                    await asyncio.sleep(self._poll_interval)
        finally:
            heartbeat_task.cancel()
            await self._repo.remove_worker(self._info.id)

    def stop(self) -> None:
        self._running = False
