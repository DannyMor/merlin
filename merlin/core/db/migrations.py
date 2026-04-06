from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from merlin.core.db.interface import Database

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 4

MIGRATIONS: list[str] = [
    # Version 1: schema_version table
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    # Version 2: event_log table
    """
    CREATE TABLE IF NOT EXISTS event_log (
        id UUID PRIMARY KEY,
        ts TIMESTAMPTZ NOT NULL,
        source TEXT NOT NULL,
        level TEXT NOT NULL,
        component TEXT NOT NULL,
        action TEXT NOT NULL,
        detail JSONB NOT NULL DEFAULT '{}',
        correlation_id UUID
    )
    """,
    # Version 3: tasks table (generic — no domain-specific columns)
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id UUID PRIMARY KEY,
        key TEXT NOT NULL UNIQUE,
        "group" TEXT NOT NULL,
        params JSONB NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'pending',
        worker_id UUID,
        retries INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 3,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        started_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        error TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_tasks_claim
        ON tasks ("group", status, created_at) WHERE status = 'pending';
    CREATE INDEX IF NOT EXISTS idx_tasks_running
        ON tasks (status) WHERE status = 'running';
    CREATE INDEX IF NOT EXISTS idx_tasks_worker
        ON tasks (worker_id) WHERE worker_id IS NOT NULL;
    """,
    # Version 4: workers table
    """
    CREATE TABLE IF NOT EXISTS workers (
        id UUID PRIMARY KEY,
        hostname TEXT NOT NULL,
        started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
]


async def get_current_version(db: Database) -> int:
    rows = await db.fetch_all("SELECT version FROM schema_version")
    if not rows:
        return 0
    return max(int(row["version"]) for row in rows)


async def ensure_schema(db: Database) -> None:
    """Apply any pending migrations to bring the database up to SCHEMA_VERSION."""
    # Always create schema_version table first
    await db.execute(MIGRATIONS[0])

    current = await get_current_version(db)
    logger.info("Current schema version: %d, target: %d", current, SCHEMA_VERSION)

    for version in range(current + 1, SCHEMA_VERSION + 1):
        if version <= len(MIGRATIONS):
            logger.info("Applying migration version %d", version)
            await db.execute(MIGRATIONS[version - 1])
            await db.execute(
                "INSERT INTO schema_version (version) VALUES (:0)",
                [version],
            )
            logger.info("Applied migration version %d", version)

    logger.info("Schema is up to date at version %d", SCHEMA_VERSION)
