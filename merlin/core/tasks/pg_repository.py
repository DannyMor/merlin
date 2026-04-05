from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from merlin.core.tasks.models import Task, TaskStatus, WorkerInfo

if TYPE_CHECKING:
    from uuid import UUID

    from merlin.core.db.interface import Database


class PgTaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, task: Task) -> bool:
        row = await self._db.fetch_one(
            """
            INSERT INTO tasks (id, key, "group", params, status,
                               retries, max_retries, created_at, updated_at)
            VALUES (:0, :1, :2, :3, :4, :5, :6, :7, :8)
            ON CONFLICT (key) DO NOTHING
            RETURNING id
            """,
            [
                str(task.id),
                task.key,
                task.group,
                json.dumps(task.params),
                task.status.value,
                task.retries,
                task.max_retries,
                task.created_at,
                task.updated_at,
            ],
        )
        return row is not None

    async def claim(self, worker_id: UUID, group: str) -> Task | None:
        now = datetime.now(timezone.utc)
        row = await self._db.fetch_one(
            """
            UPDATE tasks SET status = :0, worker_id = :1, started_at = :2, updated_at = :3
            WHERE id = (
                SELECT id FROM tasks
                WHERE "group" = :4 AND status = 'pending'
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING *
            """,
            [TaskStatus.RUNNING.value, str(worker_id), now, now, group],
        )
        if row is None:
            return None
        return self._row_to_task(row)

    async def update_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        *,
        error: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            await self._db.execute(
                """
                UPDATE tasks SET status = :0, error = :1, completed_at = :2, updated_at = :3
                WHERE id = :4
                """,
                [status.value, error, now, now, str(task_id)],
            )
        else:
            await self._db.execute(
                "UPDATE tasks SET status = :0, error = :1, updated_at = :2 WHERE id = :3",
                [status.value, error, now, str(task_id)],
            )

    async def get(self, task_id: UUID) -> Task | None:
        row = await self._db.fetch_one(
            "SELECT * FROM tasks WHERE id = :0",
            [str(task_id)],
        )
        if row is None:
            return None
        return self._row_to_task(row)

    async def find_by_status(self, status: TaskStatus) -> list[Task]:
        rows = await self._db.fetch_all(
            "SELECT * FROM tasks WHERE status = :0",
            [status.value],
        )
        return [self._row_to_task(r) for r in rows]

    async def find_stale(self, threshold_seconds: float) -> list[Task]:
        cutoff = datetime.now(timezone.utc)
        rows = await self._db.fetch_all(
            """
            SELECT t.* FROM tasks t
            LEFT JOIN workers w ON t.worker_id = w.id::text
            WHERE t.status = 'running'
            AND (w.id IS NULL
                 OR EXTRACT(EPOCH FROM (:0 - w.last_heartbeat)) > :1)
            """,
            [cutoff, threshold_seconds],
        )
        return [self._row_to_task(r) for r in rows]

    async def register_worker(self, worker: WorkerInfo) -> None:
        await self._db.execute(
            """
            INSERT INTO workers (id, hostname, started_at, last_heartbeat)
            VALUES (:0, :1, :2, :3)
            """,
            [str(worker.id), worker.hostname, worker.started_at, worker.last_heartbeat],
        )

    async def heartbeat(self, worker_id: UUID) -> None:
        await self._db.execute(
            "UPDATE workers SET last_heartbeat = :0 WHERE id = :1",
            [datetime.now(timezone.utc), str(worker_id)],
        )

    async def find_dead_workers(self, threshold_seconds: float) -> list[WorkerInfo]:
        cutoff = datetime.now(timezone.utc)
        rows = await self._db.fetch_all(
            """
            SELECT * FROM workers
            WHERE EXTRACT(EPOCH FROM (:0 - last_heartbeat)) > :1
            """,
            [cutoff, threshold_seconds],
        )
        return [
            WorkerInfo(
                id=r["id"],
                hostname=r["hostname"],
                started_at=r["started_at"],
                last_heartbeat=r["last_heartbeat"],
            )
            for r in rows
        ]

    async def remove_worker(self, worker_id: UUID) -> None:
        await self._db.execute(
            "DELETE FROM workers WHERE id = :0",
            [str(worker_id)],
        )

    def _row_to_task(self, row: dict[str, object]) -> Task:
        params_raw = row.get("params", "{}")
        params = json.loads(str(params_raw)) if isinstance(params_raw, str) else params_raw

        return Task(
            id=row["id"],  # pyright: ignore[reportArgumentType]
            key=str(row["key"]),
            group=str(row["group"]),
            params=params,  # pyright: ignore[reportArgumentType]
            status=TaskStatus(str(row["status"])),
            worker_id=row.get("worker_id"),  # pyright: ignore[reportArgumentType]
            retries=int(row.get("retries", 0)),  # pyright: ignore[reportArgumentType]
            max_retries=int(row.get("max_retries", 3)),  # pyright: ignore[reportArgumentType]
            created_at=row["created_at"],  # pyright: ignore[reportArgumentType]
            updated_at=row["updated_at"],  # pyright: ignore[reportArgumentType]
            started_at=row.get("started_at"),  # pyright: ignore[reportArgumentType]
            completed_at=row.get("completed_at"),  # pyright: ignore[reportArgumentType]
            error=row.get("error"),  # pyright: ignore[reportArgumentType]
        )
