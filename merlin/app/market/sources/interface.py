from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Protocol, runtime_checkable

import pyarrow as pa


class DataType(StrEnum):
    OHLCV = "ohlcv"
    DIVIDENDS = "dividends"
    SPLITS = "splits"
    FUNDAMENTALS = "fundamentals"


@runtime_checkable
class DataSource(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def supported_data_types(self) -> frozenset[DataType]: ...

    async def fetch(
        self,
        asset: str,
        data_type: DataType,
        from_date: date,
        to_date: date,
    ) -> pa.Table: ...
