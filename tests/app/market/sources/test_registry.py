from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa

from merlin.app.market.sources.interface import DataSource, DataType
from merlin.app.market.sources.registry import SourceRegistry

if TYPE_CHECKING:
    from datetime import date


class FakeSource:
    def __init__(self, name: str, data_types: frozenset[DataType]) -> None:
        self._name = name
        self._data_types = data_types

    @property
    def name(self) -> str:
        return self._name

    @property
    def supported_data_types(self) -> frozenset[DataType]:
        return self._data_types

    async def fetch(
        self,
        asset: str,
        data_type: DataType,
        from_date: date,
        to_date: date,
    ) -> pa.Table:
        return pa.table({"asset": [asset], "type": [data_type.value]})


def _ohlcv_source(name: str = "fake") -> FakeSource:
    return FakeSource(name, frozenset({DataType.OHLCV}))


def _multi_source(name: str = "multi") -> FakeSource:
    return FakeSource(name, frozenset({DataType.OHLCV, DataType.DIVIDENDS}))


class TestSourceRegistry:
    def test_fake_source_implements_protocol(self) -> None:
        source = _ohlcv_source()
        assert isinstance(source, DataSource)

    def test_register_and_get_by_name(self) -> None:
        registry = SourceRegistry()
        source = _ohlcv_source("yahoo")
        registry.register(source)

        result = registry.get_by_name("yahoo")
        assert result is source

    def test_get_by_name_not_found(self) -> None:
        registry = SourceRegistry()
        assert registry.get_by_name("nonexistent") is None

    def test_get_by_data_type(self) -> None:
        registry = SourceRegistry()
        ohlcv = _ohlcv_source("ohlcv_only")
        multi = _multi_source("multi")
        registry.register(ohlcv)
        registry.register(multi)

        results = registry.get_by_data_type(DataType.OHLCV)
        assert len(results) == 2

        results = registry.get_by_data_type(DataType.DIVIDENDS)
        assert len(results) == 1
        assert results[0].name == "multi"

    def test_get_by_data_type_empty(self) -> None:
        registry = SourceRegistry()
        registry.register(_ohlcv_source())

        results = registry.get_by_data_type(DataType.SPLITS)
        assert results == []

    def test_all_sources(self) -> None:
        registry = SourceRegistry()
        registry.register(_ohlcv_source("a"))
        registry.register(_multi_source("b"))

        assert len(registry.all_sources()) == 2

    def test_register_overwrites_same_name(self) -> None:
        registry = SourceRegistry()
        first = _ohlcv_source("yahoo")
        second = _multi_source("yahoo")
        registry.register(first)
        registry.register(second)

        result = registry.get_by_name("yahoo")
        assert result is second
        assert len(registry.all_sources()) == 1

    async def test_fake_source_fetch(self) -> None:
        from datetime import date

        source = _ohlcv_source()
        table = await source.fetch("AAPL", DataType.OHLCV, date(2025, 1, 1), date(2025, 1, 31))

        assert table.num_rows == 1
        assert table.column("asset")[0].as_py() == "AAPL"
