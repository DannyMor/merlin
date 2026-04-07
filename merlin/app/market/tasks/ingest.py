from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel

from merlin.app.market.sources.interface import DataSource, DataType
from merlin.core.db.interface import Database
from merlin.core.tasks.interface import ModelTaskExecutor
from merlin.core.tasks.models import Task, TaskContext

logger = logging.getLogger(__name__)


class MarketIngestParams(BaseModel):
    asset: str
    source: str
    data_type: DataType
    from_date: date
    to_date: date


class MarketIngestExecutor(ModelTaskExecutor[MarketIngestParams]):
    _params_type = MarketIngestParams

    def __init__(self, source: DataSource, db: Database) -> None:
        self._source = source
        self._db = db

    async def execute(self, ctx: TaskContext, params: MarketIngestParams) -> None:
        logger.info(
            "Ingesting %s %s from %s (%s to %s)",
            params.asset,
            params.data_type,
            params.source,
            params.from_date,
            params.to_date,
        )

        table = await self._source.fetch(
            params.asset,
            params.data_type,
            params.from_date,
            params.to_date,
        )

        logger.info(
            "Fetched %d rows for %s %s",
            table.num_rows,
            params.asset,
            params.data_type,
        )


class MarketIngestSchedule:
    def __init__(
        self,
        assets: list[str],
        data_types: list[DataType],
        source_name: str = "yahoo",
        lookback_days: int = 7,
    ) -> None:
        self._assets = assets
        self._data_types = data_types
        self._source_name = source_name
        self._lookback_days = lookback_days

    @property
    def schedule(self) -> str:
        return "@daily"

    async def generate_tasks(self) -> list[Task]:
        now = datetime.now(timezone.utc)
        from_date = (now - timedelta(days=self._lookback_days)).date()
        to_date = now.date()

        tasks: list[Task] = []
        for asset in self._assets:
            for data_type in self._data_types:
                key = f"market:ingest:{asset}:{data_type.value}:{from_date.isoformat()}"
                tasks.append(
                    Task(
                        key=key,
                        group="market.ingest",
                        params=MarketIngestParams(
                            asset=asset,
                            source=self._source_name,
                            data_type=data_type,
                            from_date=from_date,
                            to_date=to_date,
                        ).model_dump(mode="json"),
                    )
                )
        return tasks
