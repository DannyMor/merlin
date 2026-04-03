import pytest

from merlin.core.db.interface import Database, Row
from merlin.core.db.memory import InMemoryDatabase


@pytest.fixture
async def db() -> InMemoryDatabase:
    database = InMemoryDatabase()
    await database.connect()
    return database


def test_in_memory_implements_protocol() -> None:
    assert isinstance(InMemoryDatabase(), Database)


class TestInMemoryDatabase:
    async def test_connect_disconnect(self) -> None:
        db = InMemoryDatabase()
        await db.connect()
        await db.disconnect()

    async def test_create_table(self, db: InMemoryDatabase) -> None:
        await db.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER, name TEXT)")
        rows = await db.fetch_all("SELECT * FROM test")
        assert rows == []

    async def test_insert_and_fetch(self, db: InMemoryDatabase) -> None:
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER, name TEXT)")
        await db.execute("INSERT INTO users (id, name) VALUES (:0, :1)", [1, "alice"])
        await db.execute("INSERT INTO users (id, name) VALUES (:0, :1)", [2, "bob"])

        rows = await db.fetch_all("SELECT * FROM users")
        assert len(rows) == 2

    async def test_fetch_one(self, db: InMemoryDatabase) -> None:
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER, value TEXT)")
        await db.execute("INSERT INTO items (id, value) VALUES (:0, :1)", [1, "first"])

        row = await db.fetch_one("SELECT * FROM items WHERE id = :0", [1])
        assert row is not None
        assert row["id"] == 1
        assert row["value"] == "first"

    async def test_fetch_one_returns_none(self, db: InMemoryDatabase) -> None:
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER)")
        row = await db.fetch_one("SELECT * FROM items WHERE id = :0", [999])
        assert row is None

    async def test_update(self, db: InMemoryDatabase) -> None:
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER, value TEXT)")
        await db.execute("INSERT INTO items (id, value) VALUES (:0, :1)", [1, "old"])
        await db.execute("UPDATE items SET value = :0", ["new"])

        row = await db.fetch_one("SELECT * FROM items WHERE id = :0", [1])
        assert row is not None
        assert row["value"] == "new"

    async def test_delete(self, db: InMemoryDatabase) -> None:
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER)")
        await db.execute("INSERT INTO items (id) VALUES (:0)", [1])
        await db.execute("INSERT INTO items (id) VALUES (:0)", [2])
        await db.execute("DELETE FROM items WHERE id = :0", [1])

        rows = await db.fetch_all("SELECT * FROM items")
        assert len(rows) == 1
        assert rows[0]["id"] == 2

    async def test_transaction_commit(self, db: InMemoryDatabase) -> None:
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER)")

        async with db.transaction():
            await db.execute("INSERT INTO items (id) VALUES (:0)", [1])

        rows = await db.fetch_all("SELECT * FROM items")
        assert len(rows) == 1

    async def test_transaction_rollback(self, db: InMemoryDatabase) -> None:
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER)")
        await db.execute("INSERT INTO items (id) VALUES (:0)", [1])

        with pytest.raises(ValueError, match="rollback"):
            async with db.transaction():
                await db.execute("INSERT INTO items (id) VALUES (:0)", [2])
                msg = "rollback"
                raise ValueError(msg)

        rows = await db.fetch_all("SELECT * FROM items")
        assert len(rows) == 1
        assert rows[0]["id"] == 1

    async def test_not_connected_raises(self) -> None:
        db = InMemoryDatabase()
        with pytest.raises(RuntimeError, match="not connected"):
            await db.execute("SELECT 1")

    async def test_row_is_dict(self, db: InMemoryDatabase) -> None:
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER, name TEXT)")
        await db.execute("INSERT INTO items (id, name) VALUES (:0, :1)", [1, "test"])

        row = await db.fetch_one("SELECT * FROM items")
        assert row is not None
        assert isinstance(row, Row)
        assert isinstance(row, dict)
