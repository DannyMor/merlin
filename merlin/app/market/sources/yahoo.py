# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
# yfinance and pandas are untyped; this adapter bridges them to typed Arrow tables.

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import TYPE_CHECKING

import pyarrow as pa

from merlin.app.market.sources.interface import DataType
from merlin.app.market.sources.schemas import (
    DIVIDENDS_SCHEMA,
    OHLCV_SCHEMA,
    SPLITS_SCHEMA,
    empty_table,
)

if TYPE_CHECKING:
    import yfinance as yf

logger = logging.getLogger(__name__)

_SUPPORTED_TYPES = frozenset({DataType.OHLCV, DataType.DIVIDENDS, DataType.SPLITS})


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
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.fetch_sync, asset, data_type, from_date, to_date
        )

    def fetch_sync(
        self,
        asset: str,
        data_type: DataType,
        from_date: date,
        to_date: date,
    ) -> pa.Table:
        import yfinance as yf

        ticker = yf.Ticker(asset)
        start = from_date.isoformat()
        end = to_date.isoformat()

        match data_type:
            case DataType.OHLCV:
                return self.fetch_ohlcv(ticker, asset, start, end)
            case DataType.DIVIDENDS:
                return self.fetch_dividends(ticker, asset, start, end)
            case DataType.SPLITS:
                return self.fetch_splits(ticker, asset, start, end)
            case _:
                msg = f"Unsupported data type: {data_type}"
                raise ValueError(msg)

    def fetch_ohlcv(
        self,
        ticker: yf.Ticker,
        asset: str,
        start: str,
        end: str,
    ) -> pa.Table:
        df = ticker.history(start=start, end=end, auto_adjust=False)
        if df.empty:
            return empty_table(OHLCV_SCHEMA)

        df = df.reset_index()
        n = len(df)
        adj_close = df["Adj Close"].tolist() if "Adj Close" in df.columns else [None] * n
        return pa.table(
            {
                "symbol": pa.array([asset] * n, type=pa.string()),
                "market_date": pa.array(df["Date"].dt.date.tolist(), type=pa.date32()),
                "open": pa.array(df["Open"].tolist(), type=pa.float64()),
                "high": pa.array(df["High"].tolist(), type=pa.float64()),
                "low": pa.array(df["Low"].tolist(), type=pa.float64()),
                "close": pa.array(df["Close"].tolist(), type=pa.float64()),
                "volume": pa.array(df["Volume"].tolist(), type=pa.int64()),
                "adjusted_close": pa.array(adj_close, type=pa.float64()),
            }
        )

    def fetch_dividends(
        self,
        ticker: yf.Ticker,
        asset: str,
        start: str,
        end: str,
    ) -> pa.Table:
        div = ticker.dividends
        if div.empty:
            return empty_table(DIVIDENDS_SCHEMA)

        div = div.loc[start:end]
        n = len(div)
        return pa.table(
            {
                "symbol": pa.array([asset] * n, type=pa.string()),
                "market_date": pa.array(div.index.date.tolist(), type=pa.date32()),
                "amount": pa.array(div.tolist(), type=pa.float64()),
            }
        )

    def fetch_splits(
        self,
        ticker: yf.Ticker,
        asset: str,
        start: str,
        end: str,
    ) -> pa.Table:
        splits = ticker.splits
        if splits.empty:
            return empty_table(SPLITS_SCHEMA)

        splits = splits.loc[start:end]
        n = len(splits)
        return pa.table(
            {
                "symbol": pa.array([asset] * n, type=pa.string()),
                "market_date": pa.array(splits.index.date.tolist(), type=pa.date32()),
                "ratio": pa.array(splits.tolist(), type=pa.float64()),
            }
        )
