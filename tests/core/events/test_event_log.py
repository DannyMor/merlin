from datetime import datetime, timedelta, timezone
from uuid import uuid4

from merlin.core.events.memory import InMemoryEventLog
from merlin.core.events.models import Event, EventLevel, EventSource


def _make_event(
    source: EventSource = EventSource.WORKER,
    level: EventLevel = EventLevel.INFO,
    action: str = "test_action",
    timestamp: datetime | None = None,
) -> Event:
    return Event(
        source=source,
        level=level,
        component="test",
        action=action,
        timestamp=timestamp or datetime.now(timezone.utc),
    )


class TestInMemoryEventLog:
    async def test_emit_and_query(self) -> None:
        log = InMemoryEventLog()
        event = _make_event()

        await log.emit(event)

        results = await log.query()
        assert len(results) == 1
        assert results[0].id == event.id

    async def test_query_filter_by_source(self) -> None:
        log = InMemoryEventLog()
        await log.emit(_make_event(source=EventSource.WORKER))
        await log.emit(_make_event(source=EventSource.SCHEDULER))
        await log.emit(_make_event(source=EventSource.WORKER))

        results = await log.query(source=EventSource.WORKER)
        assert len(results) == 2
        assert all(e.source == EventSource.WORKER for e in results)

    async def test_query_filter_by_level(self) -> None:
        log = InMemoryEventLog()
        await log.emit(_make_event(level=EventLevel.INFO))
        await log.emit(_make_event(level=EventLevel.ERROR))
        await log.emit(_make_event(level=EventLevel.INFO))

        results = await log.query(level=EventLevel.ERROR)
        assert len(results) == 1
        assert results[0].level == EventLevel.ERROR

    async def test_query_filter_by_since(self) -> None:
        log = InMemoryEventLog()
        now = datetime.now(timezone.utc)
        old = now - timedelta(hours=2)
        recent = now - timedelta(minutes=5)

        await log.emit(_make_event(timestamp=old))
        await log.emit(_make_event(timestamp=recent))
        await log.emit(_make_event(timestamp=now))

        cutoff = now - timedelta(hours=1)
        results = await log.query(since=cutoff)
        assert len(results) == 2

    async def test_query_combined_filters(self) -> None:
        log = InMemoryEventLog()
        now = datetime.now(timezone.utc)
        old = now - timedelta(hours=2)

        await log.emit(
            _make_event(
                source=EventSource.WORKER,
                level=EventLevel.ERROR,
                timestamp=now,
            )
        )
        await log.emit(
            _make_event(
                source=EventSource.WORKER,
                level=EventLevel.INFO,
                timestamp=now,
            )
        )
        await log.emit(
            _make_event(
                source=EventSource.SCHEDULER,
                level=EventLevel.ERROR,
                timestamp=now,
            )
        )
        await log.emit(
            _make_event(
                source=EventSource.WORKER,
                level=EventLevel.ERROR,
                timestamp=old,
            )
        )

        results = await log.query(
            source=EventSource.WORKER,
            level=EventLevel.ERROR,
            since=now - timedelta(hours=1),
        )
        assert len(results) == 1

    async def test_query_limit(self) -> None:
        log = InMemoryEventLog()
        for _ in range(10):
            await log.emit(_make_event())

        results = await log.query(limit=3)
        assert len(results) == 3

    async def test_query_returns_newest_first(self) -> None:
        log = InMemoryEventLog()
        now = datetime.now(timezone.utc)

        for i in range(5):
            await log.emit(
                _make_event(
                    action=f"action_{i}",
                    timestamp=now + timedelta(seconds=i),
                )
            )

        results = await log.query()
        assert results[0].action == "action_4"
        assert results[-1].action == "action_0"

    async def test_query_empty_log(self) -> None:
        log = InMemoryEventLog()
        results = await log.query()
        assert results == []

    async def test_event_with_detail_and_correlation(self) -> None:
        log = InMemoryEventLog()
        correlation = uuid4()
        event = Event(
            source=EventSource.WORKER,
            level=EventLevel.INFO,
            component="ingestion",
            action="task_completed",
            detail={"records": 250, "asset": "AAPL"},
            correlation_id=correlation,
        )

        await log.emit(event)

        results = await log.query()
        assert len(results) == 1
        assert results[0].detail["records"] == 250
        assert results[0].correlation_id == correlation
