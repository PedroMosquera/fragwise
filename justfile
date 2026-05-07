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

# Bring up redis only (for search rate limiter + cache work).
redis-up:
    docker compose up -d redis

# Stop and remove the redis container (volume preserved).
redis-down:
    docker compose stop redis

# Open a redis-cli shell in the running redis container.
redis-shell:
    docker compose exec redis redis-cli

# Stub: future load benchmark for /api/v1/search.
search-bench:
    @echo "TODO: implement search bench"

# Apply migrations against the dev DB.
db-migrate:
    cd apps/api && uv run alembic upgrade head

# Roll all migrations back.
db-rollback:
    cd apps/api && uv run alembic downgrade base

# Drop and re-apply (dev only).
db-reset:
    cd apps/api && uv run alembic downgrade base
    cd apps/api && uv run alembic upgrade head

# Ingest ontology (notes + accords) idempotently.
ingest:
    cd apps/api && uv run python ../../data/scripts/ingest_ontology.py

# Seed ~10 example fragrances idempotently.
seed:
    cd apps/api && uv run python ../../data/scripts/seed_minimal_fragrances.py

# Embed fragrances using OpenAI. Requires OPENAI_API_KEY.
embed:
    cd apps/api && uv run python ../../data/scripts/embed_fragrances.py

# Run integration tests (requires Docker).
test-integration:
    cd apps/api && uv run pytest -m integration

# Emit a deterministic apps/api/openapi.json snapshot.
emit-openapi:
    cd apps/api && uv run python scripts/emit_openapi.py
