from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from merlin.app.market.sources.interface import DataType
from merlin.app.market.sources.yahoo import YahooFinanceSource
from merlin.app.market.tasks.ingest import MarketIngestExecutor, MarketIngestSchedule

if TYPE_CHECKING:
    from merlin.core.db.interface import Database
    from merlin.core.tasks.interface import TaskSchedule


def setup_market_worker(db: Database) -> tuple[MarketIngestExecutor, str]:
    """Wire up the market ingestion executor. Returns (executor, group)."""
    source = YahooFinanceSource()
    executor = MarketIngestExecutor(source, db)
    return executor, "market.ingest"


def setup_market_schedules(
    assets_path: Path | None = None,
) -> list[TaskSchedule]:
    """Create market-domain task schedules from config."""
    if assets_path is None:
        assets_path = Path("config/assets.yaml")

    with open(assets_path) as f:
        data = yaml.safe_load(f)

    assets = [str(asset["symbol"]) for asset in data.get("assets", [])]
    data_types = [DataType.OHLCV, DataType.DIVIDENDS, DataType.SPLITS]

    return [MarketIngestSchedule(assets, data_types)]
