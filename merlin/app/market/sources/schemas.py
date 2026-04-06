from __future__ import annotations

import pyarrow as pa

OHLCV_SCHEMA = pa.schema(
    [
        pa.field("symbol", pa.string()),
        pa.field("market_date", pa.date32()),
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("volume", pa.int64()),
        pa.field("adjusted_close", pa.float64()),
    ]
)

DIVIDENDS_SCHEMA = pa.schema(
    [
        pa.field("symbol", pa.string()),
        pa.field("market_date", pa.date32()),
        pa.field("amount", pa.float64()),
    ]
)

SPLITS_SCHEMA = pa.schema(
    [
        pa.field("symbol", pa.string()),
        pa.field("market_date", pa.date32()),
        pa.field("ratio", pa.float64()),
    ]
)


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
