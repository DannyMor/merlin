from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime

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
