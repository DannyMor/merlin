from __future__ import annotations

from merlin.app.market.sources.interface import DataSource, DataType


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, DataSource] = {}

    def register(self, source: DataSource) -> None:
        self._sources[source.name] = source

    def get_by_name(self, name: str) -> DataSource | None:
        return self._sources.get(name)

    def get_by_data_type(self, data_type: DataType) -> list[DataSource]:
        return [s for s in self._sources.values() if data_type in s.supported_data_types]

    def all_sources(self) -> list[DataSource]:
        return list(self._sources.values())
