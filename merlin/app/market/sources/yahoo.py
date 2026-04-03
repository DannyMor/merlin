# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnnecessaryCast=false
# Above: yfinance and pandas are untyped; this adapter module bridges them to typed Arrow tables.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import pyarrow as pa

from merlin.core.sources.interface import DataType

if TYPE_CHECKING:
    from datetime import date

logger = logging.getLogger(__name__)

_SUPPORTED_TYPES = frozenset({DataType.OHLCV, DataType.DIVIDENDS, DataType.SPLITS})


def empty_ohlcv_table() -> pa.Table:
    return pa.table(
        {
            "symbol": pa.array([], type=pa.string()),
            "market_date": pa.array([], type=pa.date32()),
            "open": pa.array([], type=pa.float64()),
            "high": pa.array([], type=pa.float64()),
            "low": pa.array([], type=pa.float64()),
            "close": pa.array([], type=pa.float64()),
            "volume": pa.array([], type=pa.int64()),
            "adjusted_close": pa.array([], type=pa.float64()),
        }
    )


def empty_dividends_table() -> pa.Table:
    return pa.table(
        {
            "symbol": pa.array([], type=pa.string()),
            "market_date": pa.array([], type=pa.date32()),
            "amount": pa.array([], type=pa.float64()),
        }
    )


def empty_splits_table() -> pa.Table:
    return pa.table(
        {
            "symbol": pa.array([], type=pa.string()),
            "market_date": pa.array([], type=pa.date32()),
            "ratio": pa.array([], type=pa.float64()),
        }
    )


class YahooFinanceSource:
    @property
    def name(self) -> str:
        return "yahoo"

    @property
    def supported_data_types(self) -> frozenset[DataType]:
        return _SUPPORTED_TYPES

    async def fetch(
        self,
        asset: str,
        data_type: DataType,
        from_date: date,
        to_date: date,
    ) -> pa.Table:
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._fetch_sync, asset, data_type, from_date, to_date
        )

    def _fetch_sync(
        self,
        asset: str,
        data_type: DataType,
        from_date: date,
        to_date: date,
    ) -> pa.Table:
        import yfinance as yf  # pyright: ignore[reportMissingTypeStubs]

        ticker: object = yf.Ticker(asset)  # pyright: ignore[reportUnknownMemberType]
        start = from_date.isoformat()
        end = to_date.isoformat()

        if data_type == DataType.OHLCV:
            return self._fetch_ohlcv(ticker, asset, start, end)
        if data_type == DataType.DIVIDENDS:
            return self._fetch_dividends(ticker, asset, start, end)
        if data_type == DataType.SPLITS:
            return self._fetch_splits(ticker, asset, start, end)

        msg = f"Unsupported data type: {data_type}"
        raise ValueError(msg)

    def _fetch_ohlcv(
        self,
        ticker: object,
        asset: str,
        start: str,
        end: str,
    ) -> pa.Table:
        df: object = ticker.history(  # pyright: ignore[reportAttributeAccessIssue]
            start=start, end=end, auto_adjust=False
        )
        if df.empty:  # pyright: ignore[reportAttributeAccessIssue]
            return empty_ohlcv_table()

        df = df.reset_index()  # pyright: ignore[reportAttributeAccessIssue]
        n = cast("int", len(df))  # pyright: ignore[reportArgumentType]
        has_adj = "Adj Close" in df.columns  # pyright: ignore[reportAttributeAccessIssue]
        adj_close: list[object] = (
            cast("list[object]", df["Adj Close"].tolist())  # pyright: ignore[reportIndexIssue]
            if has_adj
            else [None] * n
        )
        return pa.table(
            {
                "symbol": pa.array([asset] * n, type=pa.string()),
                "market_date": pa.array(
                    cast("list[object]", df["Date"].dt.date.tolist()),  # pyright: ignore[reportIndexIssue]
                    type=pa.date32(),
                ),
                "open": pa.array(
                    cast("list[object]", df["Open"].tolist()),  # pyright: ignore[reportIndexIssue]
                    type=pa.float64(),
                ),
                "high": pa.array(
                    cast("list[object]", df["High"].tolist()),  # pyright: ignore[reportIndexIssue]
                    type=pa.float64(),
                ),
                "low": pa.array(
                    cast("list[object]", df["Low"].tolist()),  # pyright: ignore[reportIndexIssue]
                    type=pa.float64(),
                ),
                "close": pa.array(
                    cast("list[object]", df["Close"].tolist()),  # pyright: ignore[reportIndexIssue]
                    type=pa.float64(),
                ),
                "volume": pa.array(
                    cast("list[object]", df["Volume"].tolist()),  # pyright: ignore[reportIndexIssue]
                    type=pa.int64(),
                ),
                "adjusted_close": pa.array(adj_close, type=pa.float64()),
            }
        )

    def _fetch_dividends(
        self,
        ticker: object,
        asset: str,
        start: str,
        end: str,
    ) -> pa.Table:
        div: object = ticker.dividends  # pyright: ignore[reportAttributeAccessIssue]
        if div.empty:  # pyright: ignore[reportAttributeAccessIssue]
            return empty_dividends_table()

        div = div.loc[start:end]  # pyright: ignore[reportAttributeAccessIssue]
        n = cast("int", len(div))  # pyright: ignore[reportArgumentType]
        return pa.table(
            {
                "symbol": pa.array([asset] * n, type=pa.string()),
                "market_date": pa.array(
                    cast("list[object]", div.index.date.tolist()),  # pyright: ignore[reportAttributeAccessIssue]
                    type=pa.date32(),
                ),
                "amount": pa.array(
                    cast("list[object]", div.tolist()),  # pyright: ignore[reportAttributeAccessIssue]
                    type=pa.float64(),
                ),
            }
        )

    def _fetch_splits(
        self,
        ticker: object,
        asset: str,
        start: str,
        end: str,
    ) -> pa.Table:
        splits: object = ticker.splits  # pyright: ignore[reportAttributeAccessIssue]
        if splits.empty:  # pyright: ignore[reportAttributeAccessIssue]
            return empty_splits_table()

        splits = splits.loc[start:end]  # pyright: ignore[reportAttributeAccessIssue]
        n = cast("int", len(splits))  # pyright: ignore[reportArgumentType]
        return pa.table(
            {
                "symbol": pa.array([asset] * n, type=pa.string()),
                "market_date": pa.array(
                    cast("list[object]", splits.index.date.tolist()),  # pyright: ignore[reportAttributeAccessIssue]
                    type=pa.date32(),
                ),
                "ratio": pa.array(
                    cast("list[object]", splits.tolist()),  # pyright: ignore[reportAttributeAccessIssue]
                    type=pa.float64(),
                ),
            }
        )
