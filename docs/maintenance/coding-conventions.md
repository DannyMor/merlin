# Coding Conventions

## Type System

- Strict pyright mode (`typeCheckingMode = "strict"`)
- Full type annotations required (ruff ANN rule enabled)
- `from __future__ import annotations` in every file
- `Row = dict[str, Any]` at DB boundary -- avoids type suppressions for database rows
- Only 1 `type: ignore` in production code (ModelTaskExecutor narrowing cast) -- any more is a code smell
- File-level pyright suppressions only for broken third-party stubs (pyarrow, yfinance)

## Patterns

- Protocol-based polymorphism over ABC where possible -- enables structural typing
- Generic type parameters: `TaskExecutor[T]`, `ModelTaskExecutor[T: BaseModel]`
- Explicit `_params_type: ClassVar` over introspection magic (`__init_subclass__`, `get_args`)
- Pattern matching (`match/case`) for structured branching (e.g., env var parsing)
- Pydantic for all data models and config -- runtime validation + type safety
- StrEnum for all enumerations

## Imports

- All imports at top level -- NO local imports (signals circular dependency issues being hidden)
- NO `if TYPE_CHECKING:` blocks -- the TCH ruff rule was removed. All imports are unconditional.
- Exception: heavy third-party libs can be lazy-imported inside functions (e.g., `import yfinance` in `fetch_sync()`)
- isort via ruff, known-first-party = ["merlin"]

## Async

- All IO must be async -- avoid threads
- Wrap sync APIs with `asyncio.to_thread()` when no async alternative exists
- Use `asyncio.gather()` for concurrent independent operations

## Naming

| Category        | Convention                          | Examples                                          |
|-----------------|-------------------------------------|---------------------------------------------------|
| Protocols       | Noun describing the contract        | `Database`, `EventLog`, `TaskRepository`          |
| ABCs            | Descriptor of what it does          | `TaskExecutor`                                    |
| Implementations | Prefixed by technology              | `PgTaskRepository`, `TimescaleDB`, `DuckDBEngine` |
| Test doubles    | Prefixed by Fake/Failing/Transient  | `FakeExecutor`, `FailingHeartbeatRepo`            |

## What NOT to Do

- No isinstance checks -- use Protocol/ABC dispatch
- No monkey-patching in tests -- use proper subclass doubles
- No `**kwargs: Any` -- use explicit parameters
- No correlation_id or tracking fields unless there is an active consumer
- No premature abstractions -- three similar lines is better than a helper used once
