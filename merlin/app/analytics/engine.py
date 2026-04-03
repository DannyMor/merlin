from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    import polars as pl
    import pyarrow as pa


class AnalyticsEngine:
    """Ephemeral DuckDB-based analytics engine.

    Creates an in-memory DuckDB connection, registers Arrow tables,
    and executes SQL queries returning Polars DataFrames.
    """

    def __init__(self) -> None:
        self._conn = duckdb.connect(":memory:")

    def register_table(self, name: str, table: pa.Table) -> None:
        self._conn.register(name, table)

    def query(self, sql: str) -> pl.DataFrame:
        return self._conn.sql(sql).pl()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> AnalyticsEngine:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
