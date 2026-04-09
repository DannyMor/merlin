# Tooling and CI

## Package Manager

uv (fast Python package manager from Astral)

## Linting

ruff with these rule sets:

| Rule set | Purpose            |
|----------|--------------------|
| E, W     | pycodestyle        |
| F        | pyflakes           |
| I        | isort              |
| UP       | pyupgrade          |
| B        | flake8-bugbear     |
| SIM      | flake8-simplify    |
| RUF      | ruff-specific      |
| ANN      | annotations        |

Note: TCH (type-checking imports) is deliberately disabled -- all imports are unconditional.

## Type Checking

pyright strict mode, Python 3.14 target.

## Task Runner

justfile with these commands:

| Command                      | Purpose                                    |
|------------------------------|--------------------------------------------|
| `just lint`                  | ruff check + format check                  |
| `just format`                | auto-format + auto-fix                     |
| `just typecheck`             | pyright                                    |
| `just test`                  | pytest (unit only)                         |
| `just test-all`              | pytest (including integration)             |
| `just check`                 | lint + typecheck + test (pre-push gate)    |
| `just db-up/down/reset`     | Docker compose for local TimescaleDB       |
| `just run-worker/api/orch`  | run services locally                       |
| `just build/up/down/logs`   | Docker compose orchestration               |

## Docker

Multi-stage build using uv:

1. **Builder stage** -- syncs dependencies
2. **Runtime stage** -- `python:3.14-slim` with only `.venv` and application code

## Pre-Push Workflow

Run `just check` before pushing. The gate requires:

- Zero ruff errors
- Zero pyright errors
- All 125 tests passing

## Python Version

3.14+ -- uses modern generics syntax (`class Foo[T]`), StrEnum, and pattern matching.
