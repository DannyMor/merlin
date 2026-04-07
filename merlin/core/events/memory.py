from __future__ import annotations

from datetime import datetime

from merlin.core.events.models import Event, EventLevel, EventSource


class InMemoryEventLog:
    def __init__(self) -> None:
        self._events: list[Event] = []

    async def emit(self, event: Event) -> None:
        self._events.append(event)

    async def query(
        self,
        source: EventSource | None = None,
        level: EventLevel | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Event]:
        results = self._events

        if source is not None:
            results = [e for e in results if e.source == source]

        if level is not None:
            results = [e for e in results if e.level == level]

        if since is not None:
            results = [e for e in results if e.timestamp >= since]

        return sorted(results, key=lambda e: e.timestamp, reverse=True)[:limit]
