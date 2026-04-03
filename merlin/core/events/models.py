from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class EventSource(StrEnum):
    SCHEDULER = "scheduler"
    WORKER = "worker"
    REAPER = "reaper"
    API = "api"
    SYSTEM = "system"


class Event(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: EventSource
    level: EventLevel
    component: str
    action: str
    detail: dict[str, Any] = Field(default_factory=dict)
    correlation_id: UUID | None = None
