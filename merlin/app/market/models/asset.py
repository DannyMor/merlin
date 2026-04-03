from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class AssetType(StrEnum):
    ETF = "etf"
    STOCK = "stock"
    BOND = "bond"


class Asset(BaseModel):
    symbol: str
    name: str
    asset_type: AssetType
    exchange: str = ""
    active: bool = True
