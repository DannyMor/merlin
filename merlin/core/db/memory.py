from __future__ import annotations

import re
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from merlin.core.db.interface import Row


class InMemoryDatabase:
    """In-memory database implementation for testing.

    Supports a simplified subset of SQL: CREATE TABLE IF NOT EXISTS,
    INSERT INTO, SELECT with WHERE, UPDATE with WHERE, DELETE with WHERE.
    """

    def __init__(self) -> None:
        self._tables: dict[str, list[Row]] = {}
        self._connected: bool = False
        self._in_transaction: bool = False
        self._rollback_snapshots: list[dict[str, list[Row]]] | None = None

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        self._tables.clear()

    def _check_connected(self) -> None:
        if not self._connected:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)

    async def execute(self, query: str, params: list[object] | None = None) -> None:
        self._check_connected()
        normalized = query.strip().upper()

        if normalized.startswith("CREATE TABLE"):
            self._handle_create_table(query)
        elif normalized.startswith("INSERT"):
            self._handle_insert(query, params)
        elif normalized.startswith("UPDATE"):
            self._handle_update(query, params)
        elif normalized.startswith("DELETE"):
            self._handle_delete(query, params)

    async def fetch_one(self, query: str, params: list[object] | None = None) -> Row | None:
        self._check_connected()
        rows = self._handle_select(query, params)
        return rows[0] if rows else None

    async def fetch_all(self, query: str, params: list[object] | None = None) -> list[Row]:
        self._check_connected()
        return self._handle_select(query, params)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        self._check_connected()
        snapshot = {table: [Row(row) for row in rows] for table, rows in self._tables.items()}
        self._in_transaction = True
        try:
            yield
            self._in_transaction = False
        except Exception:
            self._tables = snapshot
            self._in_transaction = False
            raise

    def _handle_create_table(self, query: str) -> None:
        match = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", query, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            if table_name not in self._tables:
                self._tables[table_name] = []

    def _handle_insert(self, query: str, params: list[object] | None) -> None:
        match = re.search(
            r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
            query,
            re.IGNORECASE,
        )
        if not match:
            return

        table_name = match.group(1)
        columns = [c.strip() for c in match.group(2).split(",")]
        value_placeholders = [v.strip() for v in match.group(3).split(",")]

        if table_name not in self._tables:
            self._tables[table_name] = []

        row = Row()
        for col, placeholder in zip(columns, value_placeholders, strict=True):
            if params is not None and placeholder.startswith(":"):
                idx = int(placeholder[1:]) if placeholder[1:].isdigit() else 0
                row[col] = params[idx] if idx < len(params) else placeholder
            elif placeholder.startswith("'") and placeholder.endswith("'"):
                row[col] = placeholder[1:-1]
            else:
                row[col] = placeholder

        self._tables[table_name].append(row)

    def _handle_select(self, query: str, params: list[object] | None) -> list[Row]:
        match = re.search(r"FROM\s+(\w+)", query, re.IGNORECASE)
        if not match:
            return []

        table_name = match.group(1)
        rows = self._tables.get(table_name, [])

        where_match = re.search(r"WHERE\s+(\w+)\s*=\s*(:?\w+|'[^']+')", query, re.IGNORECASE)
        if where_match:
            col = where_match.group(1)
            val_placeholder = where_match.group(2)
            val: object
            if params is not None and val_placeholder.startswith(":"):
                idx = int(val_placeholder[1:]) if val_placeholder[1:].isdigit() else 0
                val = params[idx] if idx < len(params) else val_placeholder
            else:
                val = val_placeholder.strip("'")
            rows = [r for r in rows if r.get(col) == val]

        return rows

    def _handle_update(self, query: str, params: list[object] | None) -> None:
        pattern = r"UPDATE\s+(\w+)\s+SET\s+(\w+)\s*=\s*(:?\w+|'[^']+')"
        match = re.search(pattern, query, re.IGNORECASE)
        if not match:
            return

        table_name = match.group(1)
        set_col = match.group(2)
        set_val_placeholder = match.group(3)

        set_val: object
        if params is not None and set_val_placeholder.startswith(":"):
            idx = int(set_val_placeholder[1:]) if set_val_placeholder[1:].isdigit() else 0
            set_val = params[idx] if idx < len(params) else set_val_placeholder
        else:
            set_val = set_val_placeholder.strip("'")

        for row in self._tables.get(table_name, []):
            row[set_col] = set_val

    def _handle_delete(self, query: str, params: list[object] | None) -> None:
        match = re.search(r"DELETE\s+FROM\s+(\w+)", query, re.IGNORECASE)
        if not match:
            return

        table_name = match.group(1)
        where_match = re.search(r"WHERE\s+(\w+)\s*=\s*(:?\w+|'[^']+')", query, re.IGNORECASE)

        if where_match and table_name in self._tables:
            col = where_match.group(1)
            val_placeholder = where_match.group(2)
            val: object
            if params is not None and val_placeholder.startswith(":"):
                idx = int(val_placeholder[1:]) if val_placeholder[1:].isdigit() else 0
                val = params[idx] if idx < len(params) else val_placeholder
            else:
                val = val_placeholder.strip("'")
            self._tables[table_name] = [r for r in self._tables[table_name] if r.get(col) != val]
        elif table_name in self._tables:
            self._tables[table_name] = []
