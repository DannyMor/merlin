# Testing Strategy

## Framework

pytest + pytest-asyncio (auto mode)

## Test Organization

```
tests/
├── conftest.py              # Shared helpers: make_task()
├── core/
│   ├── tasks/
│   │   ├── conftest.py      # Shared: FakeParams, FakeExecutor, FakeTaskSchedule
│   │   ├── test_worker.py
│   │   ├── test_scheduler.py
│   │   ├── test_reaper.py
│   │   ├── test_repository.py
│   │   └── test_models.py
│   ├── events/
│   │   └── test_event_log.py
│   ├── db/
│   │   ├── test_database.py
│   │   └── test_migrations.py
│   └── config/
│       └── test_config.py
└── app/
    └── market/
        ├── sources/
        │   ├── test_yahoo.py
        │   ├── test_schemas.py
        │   └── test_registry.py
        ├── tasks/
        │   └── test_ingest.py
        ├── db/
        │   └── test_migrations.py
        └── test_bootstrap.py
```

## In-Memory Implementations

These are full implementations, not mocks:

- **InMemoryDatabase** -- simplified SQL parser, dict-based storage, supports CREATE/INSERT/SELECT/UPDATE/DELETE
- **InMemoryTaskRepository** -- full TaskRepository implementation using in-memory dicts
- **InMemoryEventLog** -- list-based event storage with filtering

## Test Doubles via Subclassing

Test doubles are created by subclassing in-memory implementations, not by monkey-patching:

```python
class FailingHeartbeatRepo(InMemoryTaskRepository):
    async def heartbeat(self, worker_id: UUID) -> None:
        raise ConnectionError("DB unavailable")

class TransientHeartbeatRepo(InMemoryTaskRepository):
    def __init__(self) -> None:
        super().__init__()
        self._heartbeat_calls = 0

    async def heartbeat(self, worker_id: UUID) -> None:
        self._heartbeat_calls += 1
        if self._heartbeat_calls == 1:
            raise ConnectionError("Transient failure")
        await super().heartbeat(worker_id)
```

## Shared Fixtures

- `tests/conftest.py`: `make_task(key, group, params)` -- factory for Task objects
- `tests/core/tasks/conftest.py`: `FakeParams`, `FakeExecutor`, `FakeTaskSchedule`

## Integration Tests

Marked with `@pytest.mark.integration`, excluded by default:

```
pytest -m "not integration"
```

Integration tests require Docker services (TimescaleDB, etc.) to be running.

## Key Principles

- No mocking framework -- no MagicMock for production code behavior
- Test the behavior, not the implementation
- Each test file mirrors the source file it tests
- Shared helpers live in conftest.py at the appropriate scope
