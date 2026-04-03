from merlin.core.db.memory import InMemoryDatabase
from merlin.core.db.migrations import ensure_schema, get_current_version


class TestMigrations:
    async def test_ensure_schema_creates_version_table(self) -> None:
        db = InMemoryDatabase()
        await db.connect()

        await ensure_schema(db)

        rows = await db.fetch_all("SELECT * FROM schema_version")
        assert len(rows) == 1
        assert rows[0]["version"] == 1

    async def test_ensure_schema_is_idempotent(self) -> None:
        db = InMemoryDatabase()
        await db.connect()

        await ensure_schema(db)
        await ensure_schema(db)

        rows = await db.fetch_all("SELECT * FROM schema_version")
        assert len(rows) == 1

    async def test_get_current_version_empty(self) -> None:
        db = InMemoryDatabase()
        await db.connect()
        await db.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)")

        version = await get_current_version(db)
        assert version == 0

    async def test_get_current_version_after_migration(self) -> None:
        db = InMemoryDatabase()
        await db.connect()

        await ensure_schema(db)

        version = await get_current_version(db)
        assert version == 1
