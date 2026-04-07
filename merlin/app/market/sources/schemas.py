# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyarrow stubs type Schema.field() as Field[Unknown]; no workaround exists.
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


def empty_table(schema: pa.Schema) -> pa.Table:
    """Create an empty PyArrow table matching the given schema."""
    return pa.table(
        {schema.field(i).name: pa.array([], type=schema.field(i).type) for i in range(len(schema))}
    )
