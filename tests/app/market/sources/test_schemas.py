from __future__ import annotations

import pyarrow as pa

from merlin.app.market.sources.schemas import (
    DIVIDENDS_SCHEMA,
    OHLCV_SCHEMA,
    SPLITS_SCHEMA,
    empty_table,
)


class TestSchemas:
    def test_ohlcv_schema_fields(self) -> None:
        names = OHLCV_SCHEMA.names
        assert "symbol" in names
        assert "market_date" in names
        assert "open" in names
        assert "close" in names
        assert "volume" in names
        assert "adjusted_close" in names

    def test_dividends_schema_fields(self) -> None:
        names = DIVIDENDS_SCHEMA.names
        assert "symbol" in names
        assert "market_date" in names
        assert "amount" in names

    def test_splits_schema_fields(self) -> None:
        names = SPLITS_SCHEMA.names
        assert "symbol" in names
        assert "market_date" in names
        assert "ratio" in names


class TestEmptyTables:
    def test_empty_ohlcv_table(self) -> None:
        table = empty_table(OHLCV_SCHEMA)
        assert isinstance(table, pa.Table)
        assert table.num_rows == 0
        assert table.schema == OHLCV_SCHEMA

    def test_empty_dividends_table(self) -> None:
        table = empty_table(DIVIDENDS_SCHEMA)
        assert isinstance(table, pa.Table)
        assert table.num_rows == 0
        assert table.schema == DIVIDENDS_SCHEMA

    def test_empty_splits_table(self) -> None:
        table = empty_table(SPLITS_SCHEMA)
        assert isinstance(table, pa.Table)
        assert table.num_rows == 0
        assert table.schema == SPLITS_SCHEMA
