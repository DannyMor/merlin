# Merlin task runner

# Linting and formatting
lint:
    uv run ruff check .
    uv run ruff format --check .

format:
    uv run ruff format .
    uv run ruff check --fix .

typecheck:
    uv run pyright

# Testing
test:
    uv run pytest -m "not integration"

test-all:
    uv run pytest

# Pre-push gate
check: lint typecheck test

# Database
db-up:
    docker compose up timescaledb -d

db-down:
    docker compose down

db-reset: db-down
    docker volume rm merlin_timescaledb_data || true
    just db-up

# Run services
run-worker:
    uv run merlin-worker

run-api:
    uv run merlin-api

run-orch:
    uv run merlin-orchestrator

# Docker
build:
    docker compose build

up:
    docker compose up -d

down:
    docker compose down

logs service="":
    docker compose logs -f {{ service }}
