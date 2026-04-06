from merlin.app.market.db.migrations import (
    MARKET_SCHEMA_VERSION,
    ensure_market_schema,
    get_market_version,
)
from merlin.core.db.memory import InMemoryDatabase


class TestMarketMigrations:
    async def test_ensure_market_schema(self) -> None:
        db = InMemoryDatabase()
        await db.connect()

        await ensure_market_schema(db)

        rows = await db.fetch_all("SELECT * FROM market_schema_version")
        assert len(rows) == MARKET_SCHEMA_VERSION

    async def test_ensure_market_schema_is_idempotent(self) -> None:
        db = InMemoryDatabase()
        await db.connect()

        await ensure_market_schema(db)
        await ensure_market_schema(db)

        rows = await db.fetch_all("SELECT * FROM market_schema_version")
        assert len(rows) == MARKET_SCHEMA_VERSION

    async def test_get_market_version_empty(self) -> None:
        db = InMemoryDatabase()
        await db.connect()

        version = await get_market_version(db)
        assert version == 0

    async def test_get_market_version_after_migration(self) -> None:
        db = InMemoryDatabase()
        await db.connect()

        await ensure_market_schema(db)

        version = await get_market_version(db)
        assert version == MARKET_SCHEMA_VERSION
