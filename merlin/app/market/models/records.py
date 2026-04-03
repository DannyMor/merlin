from __future__ import annotations

from datetime import date  # noqa: TC003 - Pydantic needs this at runtime

from pydantic import BaseModel


class OHLCVRecord(BaseModel):
    symbol: str
    market_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: float | None = None


class DividendRecord(BaseModel):
    symbol: str
    market_date: date
    amount: float


class SplitRecord(BaseModel):
    symbol: str
    market_date: date
    ratio: float
