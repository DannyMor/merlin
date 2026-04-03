from __future__ import annotations

import json
from typing import TYPE_CHECKING

from merlin.core.events.models import Event, EventLevel, EventSource

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from merlin.core.db.interface import Database


class PgEventLog:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def emit(self, event: Event) -> None:
        await self._db.execute(
            """
            INSERT INTO event_log (id, ts, source, level, component, action, detail, correlation_id)
            VALUES (:0, :1, :2, :3, :4, :5, :6, :7)
            """,
            [
                str(event.id),
                event.timestamp.isoformat(),
                event.source.value,
                event.level.value,
                event.component,
                event.action,
                json.dumps(event.detail),
                str(event.correlation_id) if event.correlation_id is not None else None,
            ],
        )

    async def query(
        self,
        source: EventSource | None = None,
        level: EventLevel | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Event]:
        conditions: list[str] = []
        params: list[object] = []
        idx = 0

        if source is not None:
            conditions.append(f"source = :{idx}")
            params.append(source.value)
            idx += 1

        if level is not None:
            conditions.append(f"level = :{idx}")
            params.append(level.value)
            idx += 1

        if since is not None:
            conditions.append(f"ts >= :{idx}")
            params.append(since.isoformat())
            idx += 1

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM event_log{where} ORDER BY ts DESC LIMIT :{idx}"
        params.append(limit)

        rows = await self._db.fetch_all(query, params)
        return [self._row_to_event(row) for row in rows]

    @staticmethod
    def _row_to_event(row: dict[str, object]) -> Event:
        correlation_id_raw = row.get("correlation_id")
        correlation_id: UUID | None = None
        if correlation_id_raw is not None:
            from uuid import UUID as UUIDType

            correlation_id = UUIDType(str(correlation_id_raw))

        detail_raw = row.get("detail", "{}")
        detail: dict[str, object] = (
            json.loads(str(detail_raw)) if isinstance(detail_raw, str) else {}
        )

        return Event(
            id=str(row["id"]),  # type: ignore[arg-type]
            timestamp=str(row["ts"]),  # type: ignore[arg-type]
            source=EventSource(str(row["source"])),
            level=EventLevel(str(row["level"])),
            component=str(row["component"]),
            action=str(row["action"]),
            detail=detail,
            correlation_id=correlation_id,
        )
