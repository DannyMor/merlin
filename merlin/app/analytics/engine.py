from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import duckdb

if TYPE_CHECKING:
    import polars as pl
    import pyarrow as pa


class AnalyticsEngine(Protocol):
    def register_table(self, name: str, table: pa.Table) -> None: ...
    def query(self, sql: str) -> pl.DataFrame: ...
    def close(self) -> None: ...


class DuckDBEngine:
    """Ephemeral in-memory DuckDB engine."""

    def __init__(self) -> None:
        self._conn = duckdb.connect(":memory:")

    def register_table(self, name: str, table: pa.Table) -> None:
        self._conn.register(name, table)

    def query(self, sql: str) -> pl.DataFrame:
        return self._conn.sql(sql).pl()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> DuckDBEngine:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
