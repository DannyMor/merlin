from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy import CursorResult, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from merlin.core.db.interface import Row

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from merlin.core.config.models import DatabaseConfig

logger = logging.getLogger(__name__)


class TimescaleDB:
    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._engine: AsyncEngine | None = None

    async def connect(self) -> None:
        self._engine = create_async_engine(
            self._config.dsn,
            pool_size=self._config.pool_max_size,
            pool_pre_ping=True,
        )
        logger.info("Connected to TimescaleDB at %s:%s", self._config.host, self._config.port)

    async def disconnect(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            logger.info("Disconnected from TimescaleDB")

    def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._engine

    async def execute(self, query: str, params: list[object] | None = None) -> None:
        engine = self._get_engine()
        async with engine.begin() as conn:
            await self._execute(conn, query, params)

    async def fetch_one(self, query: str, params: list[object] | None = None) -> Row | None:
        engine = self._get_engine()
        async with engine.connect() as conn:
            result = await self._execute(conn, query, params)
            row = result.mappings().fetchone()
            return Row(row) if row is not None else None

    async def fetch_all(self, query: str, params: list[object] | None = None) -> list[Row]:
        engine = self._get_engine()
        async with engine.connect() as conn:
            result = await self._execute(conn, query, params)
            return [Row(row) for row in result.mappings().fetchall()]

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        engine = self._get_engine()
        async with engine.begin():
            yield

    @staticmethod
    async def _execute(
        conn: AsyncConnection, query: str, params: list[object] | None
    ) -> CursorResult[object]:
        stmt = text(query)
        if params is not None:
            param_dict = {str(i): v for i, v in enumerate(params)}
            return await conn.execute(stmt, param_dict)
        return await conn.execute(stmt)
