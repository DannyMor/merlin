from __future__ import annotations

import asyncio
import logging

from merlin.core.events.interface import EventLog
from merlin.core.events.models import Event, EventLevel, EventSource
from merlin.core.tasks.interface import TaskRepository
from merlin.core.tasks.models import TaskStatus

logger = logging.getLogger(__name__)


class Reaper:
    def __init__(
        self,
        repository: TaskRepository,
        event_log: EventLog,
        stale_threshold: float = 60.0,
        max_retries: int = 3,
        poll_interval: float = 30.0,
    ) -> None:
        self._repo = repository
        self._event_log = event_log
        self._stale_threshold = stale_threshold
        self._max_retries = max_retries
        self._poll_interval = poll_interval
        self._running = False

    async def tick(self) -> int:
        """Run one reap cycle. Returns number of tasks reaped."""
        stale = await self._repo.find_stale(self._stale_threshold)
        reaped = 0

        for task in stale:
            if task.retries >= self._max_retries:
                await self._repo.update_status(
                    task.id, TaskStatus.DEAD, error="Max retries exceeded"
                )
                await self._event_log.emit(
                    Event(
                        source=EventSource.REAPER,
                        level=EventLevel.ERROR,
                        component="reaper",
                        action="task_dead",
                        detail={
                            "task_id": str(task.id),
                            "retries": task.retries,
                        },
                    )
                )
            else:
                await self._repo.update_status(
                    task.id, TaskStatus.PENDING, retries=task.retries + 1
                )
                await self._event_log.emit(
                    Event(
                        source=EventSource.REAPER,
                        level=EventLevel.WARN,
                        component="reaper",
                        action="task_reset",
                        detail={
                            "task_id": str(task.id),
                            "retries": task.retries + 1,
                        },
                    )
                )
            reaped += 1

        # Clean up dead workers
        dead_workers = await self._repo.find_dead_workers(self._stale_threshold)
        for worker in dead_workers:
            await self._repo.remove_worker(worker.id)
            await self._event_log.emit(
                Event(
                    source=EventSource.REAPER,
                    level=EventLevel.WARN,
                    component="reaper",
                    action="worker_removed",
                    detail={"worker_id": str(worker.id)},
                )
            )

        if reaped > 0:
            logger.info("Reaper processed %d stale tasks", reaped)
        return reaped

    async def run(self) -> None:
        self._running = True
        logger.info("Reaper starting with %.1fs interval", self._poll_interval)
        while self._running:
            await self.tick()
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False
