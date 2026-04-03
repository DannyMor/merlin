FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY merlin/ merlin/
COPY config/ config/
RUN uv sync --frozen --no-dev

FROM python:3.14-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/merlin /app/merlin
COPY --from=builder /app/config /app/config

ENV PATH="/app/.venv/bin:$PATH"
