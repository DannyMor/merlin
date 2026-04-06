from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    key: str
    group: str
    params: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    worker_id: UUID | None = None
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class TaskContext(BaseModel):
    """Read-only metadata exposed to task executors."""

    id: UUID
    key: str
    group: str
    retries: int
    created_at: datetime


class WorkerInfo(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    hostname: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
