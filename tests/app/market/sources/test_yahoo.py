from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pyarrow as pa

from merlin.app.market.sources.interface import DataSource, DataType
from merlin.app.market.sources.schemas import (
    empty_dividends_table,
    empty_ohlcv_table,
    empty_splits_table,
)
from merlin.app.market.sources.yahoo import YahooFinanceSource


def _mock_ohlcv_ticker() -> MagicMock:
    """Create a mock yf.Ticker that returns OHLCV data."""
    ticker = MagicMock()
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.reset_index.return_value = mock_df
    mock_df.__len__ = lambda _self: 2  # pyright: ignore[reportAssignmentType, reportUnknownLambdaType]
    mock_df.columns = ["Date", "Open", "High", "Low", "Close", "Volume", "Adj Close"]
    mock_df.__getitem__ = _mock_getitem
    ticker.history.return_value = mock_df
    return ticker


def _mock_empty_ticker() -> MagicMock:
    """Create a mock yf.Ticker that returns empty data."""
    ticker = MagicMock()
    ticker.history.return_value = MagicMock(empty=True)
    ticker.dividends = MagicMock(empty=True)
    ticker.splits = MagicMock(empty=True)
    return ticker


def _mock_getitem(_self: object, key: str) -> MagicMock:
    col = MagicMock()
    if key == "Date":
        col.dt.date.tolist.return_value = [date(2025, 1, 15), date(2025, 1, 16)]
    elif key == "Volume":
        col.tolist.return_value = [50000000, 45000000]
    elif key == "Adj Close":
        col.tolist.return_value = [152.5, 153.5]
    else:
        col.tolist.return_value = [150.0, 151.0]
    return col


class TestYahooFinanceSource:
    def test_implements_protocol(self) -> None:
        source = YahooFinanceSource()
        assert isinstance(source, DataSource)

    def test_name(self) -> None:
        source = YahooFinanceSource()
        assert source.name == "yahoo"

    def test_supported_data_types(self) -> None:
        source = YahooFinanceSource()
        assert DataType.OHLCV in source.supported_data_types
        assert DataType.DIVIDENDS in source.supported_data_types
        assert DataType.SPLITS in source.supported_data_types
        assert DataType.FUNDAMENTALS not in source.supported_data_types

    def test_empty_ohlcv_table(self) -> None:
        table = empty_ohlcv_table()
        assert isinstance(table, pa.Table)
        assert table.num_rows == 0
        assert "symbol" in table.column_names
        assert "market_date" in table.column_names

    def test_empty_dividends_table(self) -> None:
        table = empty_dividends_table()
        assert isinstance(table, pa.Table)
        assert table.num_rows == 0

    def test_empty_splits_table(self) -> None:
        table = empty_splits_table()
        assert isinstance(table, pa.Table)
        assert table.num_rows == 0

    def test_fetch_ohlcv_with_data(self) -> None:
        source = YahooFinanceSource()
        ticker = _mock_ohlcv_ticker()

        table = source._fetch_ohlcv(ticker, "AAPL", "2025-01-15", "2025-01-16")  # pyright: ignore[reportPrivateUsage]

        assert isinstance(table, pa.Table)
        assert table.num_rows == 2
        assert "symbol" in table.column_names
        assert "market_date" in table.column_names

    def test_fetch_ohlcv_empty(self) -> None:
        source = YahooFinanceSource()
        ticker = _mock_empty_ticker()

        table = source._fetch_ohlcv(ticker, "AAPL", "2025-01-15", "2025-01-16")  # pyright: ignore[reportPrivateUsage]

        assert isinstance(table, pa.Table)
        assert table.num_rows == 0

    def test_fetch_dividends_empty(self) -> None:
        source = YahooFinanceSource()
        ticker = _mock_empty_ticker()

        table = source._fetch_dividends(ticker, "AAPL", "2025-01-01", "2025-12-31")  # pyright: ignore[reportPrivateUsage]

        assert isinstance(table, pa.Table)
        assert table.num_rows == 0

    def test_fetch_splits_empty(self) -> None:
        source = YahooFinanceSource()
        ticker = _mock_empty_ticker()

        table = source._fetch_splits(ticker, "AAPL", "2025-01-01", "2025-12-31")  # pyright: ignore[reportPrivateUsage]

        assert isinstance(table, pa.Table)
        assert table.num_rows == 0
