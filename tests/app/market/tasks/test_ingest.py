from __future__ import annotations

from datetime import date, datetime, timezone

import pyarrow as pa

from merlin.app.market.tasks.ingest import MarketIngestExecutor, MarketScheduleSource
from merlin.core.db.memory import InMemoryDatabase
from merlin.core.sources.interface import DataType
from merlin.core.tasks.models import Task


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
            asset="AAPL",
            source="fake",
            data_type="ohlcv",
            from_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )

        await executor.execute(task)

        assert len(source.fetched) == 1
        assert source.fetched[0][0] == "AAPL"
        assert source.fetched[0][1] == DataType.OHLCV


class TestMarketScheduleSource:
    async def test_generate_tasks(self) -> None:
        schedule = MarketScheduleSource(
            assets=["AAPL", "MSFT"],
            data_types=[DataType.OHLCV],
            source_name="yahoo",
            lookback_days=7,
        )

        tasks = await schedule.generate_tasks()

        assert len(tasks) == 2
        symbols = {t.asset for t in tasks}
        assert symbols == {"AAPL", "MSFT"}
        assert all(t.source == "yahoo" for t in tasks)
        assert all(t.data_type == "ohlcv" for t in tasks)

    async def test_generate_tasks_multiple_data_types(self) -> None:
        schedule = MarketScheduleSource(
            assets=["AAPL"],
            data_types=[DataType.OHLCV, DataType.DIVIDENDS],
        )

        tasks = await schedule.generate_tasks()

        assert len(tasks) == 2
        data_types = {t.data_type for t in tasks}
        assert data_types == {"ohlcv", "dividends"}
