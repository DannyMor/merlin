from __future__ import annotations

from pydantic import BaseModel

from merlin.core.tasks.interface import ModelTaskExecutor
from merlin.core.tasks.models import Task, TaskContext


class FakeParams(BaseModel):
    value: str = "test"


class FakeExecutor(ModelTaskExecutor[FakeParams]):
    _params_type = FakeParams

    def __init__(self, *, fail: bool = False) -> None:
        self.executed: list[tuple[TaskContext, FakeParams]] = []
        self._fail = fail

    async def execute(self, ctx: TaskContext, params: FakeParams) -> None:
        self.executed.append((ctx, params))
        if self._fail:
            msg = "Simulated failure"
            raise RuntimeError(msg)


class FakeTaskSchedule:
    def __init__(self, tasks: list[Task]) -> None:
        self.tasks = tasks

    @property
    def schedule(self) -> str:
        return "@daily"

    async def generate_tasks(self) -> list[Task]:
        return self.tasks
