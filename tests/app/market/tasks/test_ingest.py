from __future__ import annotations

from datetime import date

import pyarrow as pa

from merlin.app.market.sources.interface import DataType
from merlin.app.market.tasks.ingest import (
    MarketIngestExecutor,
    MarketIngestParams,
    MarketIngestSchedule,
)
from merlin.core.db.memory import InMemoryDatabase
from merlin.core.tasks.models import Task, TaskContext


class FakeSource:
    def __init__(self) -> None:
        self.fetched: list[tuple[str, DataType, date, date]] = []

    @property
    def name(self) -> str:
        return "fake"

    @property
    def supported_data_types(self) -> frozenset[DataType]:
        return frozenset({DataType.OHLCV})

    async def fetch(
        self,
        asset: str,
        data_type: DataType,
        from_date: date,
        to_date: date,
    ) -> pa.Table:
        self.fetched.append((asset, data_type, from_date, to_date))
        return pa.table({"symbol": [asset], "value": [1.0]})


class TestMarketIngestExecutor:
    async def test_execute_fetches_data(self) -> None:
        source = FakeSource()
        db = InMemoryDatabase()
        await db.connect()
        executor = MarketIngestExecutor(source, db)

        task = Task(
            key="market:ingest:AAPL:ohlcv:2025-01-01",
            group="market.ingest",
            params={
                "asset": "AAPL",
                "source": "fake",
                "data_type": "ohlcv",
                "from_date": "2025-01-01",
                "to_date": "2025-01-31",
            },
        )
        ctx = TaskContext(
            id=task.id,
            key=task.key,
            group=task.group,
            retries=task.retries,
            created_at=task.created_at,
        )
        params = executor.parse_params(task.params)

        await executor.execute(ctx, params)

        assert len(source.fetched) == 1
        assert source.fetched[0][0] == "AAPL"
        assert source.fetched[0][1] == DataType.OHLCV

    async def test_parse_params(self) -> None:
        source = FakeSource()
        db = InMemoryDatabase()
        await db.connect()
        executor = MarketIngestExecutor(source, db)

        params = executor.parse_params(
            {
                "asset": "MSFT",
                "source": "yahoo",
                "data_type": "ohlcv",
                "from_date": "2025-01-01",
                "to_date": "2025-01-31",
            }
        )
        assert isinstance(params, MarketIngestParams)
        assert params.asset == "MSFT"


class TestMarketIngestSchedule:
    async def test_generate_tasks(self) -> None:
        schedule = MarketIngestSchedule(
            assets=["AAPL", "MSFT"],
            data_types=[DataType.OHLCV],
            source_name="yahoo",
            lookback_days=7,
        )

        tasks = await schedule.generate_tasks()

        assert len(tasks) == 2
        keys = {t.key for t in tasks}
        assert any("AAPL" in k for k in keys)
        assert any("MSFT" in k for k in keys)
        assert all(t.group == "market.ingest" for t in tasks)
        assert all(t.params["source"] == "yahoo" for t in tasks)

    async def test_generate_tasks_multiple_data_types(self) -> None:
        schedule = MarketIngestSchedule(
            assets=["AAPL"],
            data_types=[DataType.OHLCV, DataType.DIVIDENDS],
        )

        tasks = await schedule.generate_tasks()

        assert len(tasks) == 2
        data_types = {t.params["data_type"] for t in tasks}
        assert data_types == {"ohlcv", "dividends"}

    def test_schedule_property(self) -> None:
        schedule = MarketIngestSchedule(
            assets=["AAPL"],
            data_types=[DataType.OHLCV],
        )
        assert schedule.schedule == "@daily"
