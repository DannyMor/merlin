from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from merlin.core.sources.interface import DataType
from merlin.core.tasks.models import Task

if TYPE_CHECKING:
    from merlin.core.db.interface import Database
    from merlin.core.sources.interface import DataSource

logger = logging.getLogger(__name__)


class MarketIngestExecutor:
    def __init__(self, source: DataSource, db: Database) -> None:
        self._source = source
        self._db = db

    async def execute(self, task: Task) -> None:
        data_type = DataType(task.data_type)
        from_date = task.from_date.date()
        to_date = task.to_date.date()

        logger.info(
            "Ingesting %s %s from %s (%s to %s)",
            task.asset,
            data_type,
            task.source,
            from_date,
            to_date,
        )

        table = await self._source.fetch(
            task.asset,
            data_type,
            from_date,
            to_date,
        )

        logger.info(
            "Fetched %d rows for %s %s",
            table.num_rows,
            task.asset,
            data_type,
        )


class MarketScheduleSource:
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

    async def generate_tasks(self) -> list[Task]:
        now = datetime.now(timezone.utc)
        from_date = now - timedelta(days=self._lookback_days)

        tasks: list[Task] = []
        for asset in self._assets:
            for data_type in self._data_types:
                tasks.append(
                    Task(
                        asset=asset,
                        source=self._source_name,
                        data_type=data_type.value,
                        from_date=from_date,
                        to_date=now,
                    )
                )
        return tasks
