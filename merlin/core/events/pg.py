from __future__ import annotations

import json
from datetime import datetime

from merlin.core.db.interface import Database, Row
from merlin.core.events.models import Event, EventLevel, EventSource


class PgEventLog:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def emit(self, event: Event) -> None:
        await self._db.execute(
            """
            INSERT INTO event_log (id, ts, source, level, component, action, detail)
            VALUES (:0, :1, :2, :3, :4, :5, :6)
            """,
            [
                str(event.id),
                event.timestamp.isoformat(),
                event.source.value,
                event.level.value,
                event.component,
                event.action,
                json.dumps(event.detail),
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

        for condition, value in [
            ("source = :{idx}", source.value if source else None),
            ("level = :{idx}", level.value if level else None),
            ("ts >= :{idx}", since.isoformat() if since else None),
        ]:
            if value is not None:
                conditions.append(condition.format(idx=len(params)))
                params.append(value)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM event_log{where} ORDER BY ts DESC LIMIT :{len(params)}"
        params.append(limit)

        rows = await self._db.fetch_all(query, params)
        return [self._row_to_event(row) for row in rows]

    @staticmethod
    def _row_to_event(row: Row) -> Event:
        detail_raw = row.get("detail", "{}")
        detail: dict[str, object] = json.loads(detail_raw) if isinstance(detail_raw, str) else {}

        return Event(
            id=row["id"],
            timestamp=row["ts"],
            source=EventSource(row["source"]),
            level=EventLevel(row["level"]),
            component=row["component"],
            action=row["action"],
            detail=detail,
        )
