from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager


class Row(dict[str, Any]):
    """A database row as a string-keyed dictionary."""


@runtime_checkable
class Database(Protocol):
    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def execute(self, query: str, params: list[object] | None = None) -> None: ...

    async def fetch_one(self, query: str, params: list[object] | None = None) -> Row | None: ...

    async def fetch_all(self, query: str, params: list[object] | None = None) -> list[Row]: ...

    def transaction(self) -> AbstractAsyncContextManager[None]: ...
