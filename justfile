# Fragwise developer recipes. Requires: just, pnpm, uv, docker.

set shell := ["bash", "-cu"]

# Default recipe: list available commands.
default:
    @just --list

# Install both toolchains: pnpm workspace + Python venv via uv.
install:
    pnpm install
    cd apps/api && uv sync

# Run web (3000) + api (8000) concurrently. POSIX-only; Windows users run
# dev-web and dev-api in separate terminals.
dev:
    bash -c 'just dev-web & just dev-api & wait'

# Start the Next.js dev server on port 3000.
dev-web:
    pnpm --filter web dev

# Start the FastAPI dev server on port 8000 with autoreload.
dev-api:
    cd apps/api && uv run uvicorn fragwise_api.main:app --reload --host 127.0.0.1 --port 8000

# Run all tests across the monorepo.
test: test-web test-api

# Run vitest in apps/web.
test-web:
    pnpm --filter web test

# Run pytest in apps/api.
test-api:
    cd apps/api && uv run pytest

# Run all linters and type checkers.
lint: lint-web lint-api

# Lint + typecheck apps/web.
lint-web:
    pnpm --filter web lint
    pnpm --filter web typecheck

# Ruff + mypy strict in apps/api.
lint-api:
    cd apps/api && uv run ruff check .
    cd apps/api && uv run ruff format --check .
    cd apps/api && uv run mypy src

# Bring up postgres + redis detached.
db-up:
    docker compose up -d postgres redis

# Stop and remove postgres + redis containers (volumes preserved).
db-down:
    docker compose down

# Open a psql shell in the running postgres container.
db-shell:
    docker compose exec postgres psql -U fragwise -d fragwise
