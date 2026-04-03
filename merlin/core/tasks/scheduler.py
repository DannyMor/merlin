from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from merlin.core.events.models import Event, EventLevel, EventSource

if TYPE_CHECKING:
    from merlin.core.events.interface import EventLog
    from merlin.core.tasks.interface import ScheduleSource, TaskRepository

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        repository: TaskRepository,
        event_log: EventLog,
        sources: list[ScheduleSource],
        poll_interval: float = 60.0,
    ) -> None:
        self._repo = repository
        self._event_log = event_log
        self._sources = sources
        self._poll_interval = poll_interval
        self._running = False

    async def tick(self) -> int:
        """Run one scheduling cycle. Returns number of tasks created."""
        created = 0
        for source in self._sources:
            tasks = await source.generate_tasks()
            for task in tasks:
                if await self._repo.create(task):
                    created += 1
                    await self._event_log.emit(
                        Event(
                            source=EventSource.SCHEDULER,
                            level=EventLevel.INFO,
                            component="scheduler",
                            action="task_created",
                            detail={
                                "task_id": str(task.id),
                                "asset": task.asset,
                                "data_type": task.data_type,
                            },
                        )
                    )
        if created > 0:
            logger.info("Scheduler created %d tasks", created)
        return created

    async def run(self) -> None:
        self._running = True
        logger.info("Scheduler starting with %.1fs interval", self._poll_interval)
        while self._running:
            await self.tick()
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False
