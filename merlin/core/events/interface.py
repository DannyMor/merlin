from __future__ import annotations

from datetime import datetime
from typing import Protocol

from merlin.core.events.models import Event, EventLevel, EventSource


class EventLog(Protocol):
    async def emit(self, event: Event) -> None: ...

    async def query(
        self,
        source: EventSource | None = None,
        level: EventLevel | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Event]: ...
