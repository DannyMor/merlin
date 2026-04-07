from __future__ import annotations

from typing import Any

from merlin.core.tasks.models import Task


def make_task(
    key: str = "test:1",
    group: str = "test",
    params: dict[str, Any] | None = None,
) -> Task:
    return Task(key=key, group=group, params=params or {})
