# api-app Specification

## Purpose

Defines the FastAPI service scaffold at `apps/api/`: app-factory pattern with no-op lifespan, `/healthz` liveness endpoint, LangGraph 1.x stub (no LangChain, no heavy ML deps), uv single-project layout, ruff + mypy strict + pytest tooling, and a runnable Dockerfile for the Fly.io path.

## Requirements

### Requirement: API Project Layout

`apps/api/pyproject.toml` MUST exist as a uv-managed single-project manifest. Source code MUST live under `apps/api/src/fragwise_api/`. `apps/api/src/fragwise_api/main.py` MUST export a module-level binding `app: FastAPI`. `apps/api/uv.lock` MUST be tracked by git.

#### Scenario: Package structure and lockfile present

- GIVEN `apps/api/`
- WHEN listing files
- THEN `pyproject.toml`, `uv.lock`, and `src/fragwise_api/main.py` are tracked
- AND `main.py` exposes a top-level `app` symbol of type `FastAPI`

### Requirement: Python Version Pin

`apps/api/pyproject.toml` MUST declare `requires-python = ">=3.12,<3.13"`. `apps/api/.python-version` SHOULD be present and pin to `3.12`.

#### Scenario: Python 3.12 pinned

- GIVEN `apps/api/pyproject.toml`
- WHEN parsing the `[project]` table
- THEN `requires-python` equals `>=3.12,<3.13`
- AND any `.python-version` file contains `3.12`

### Requirement: Healthz Liveness Endpoint

`GET /healthz` MUST respond with HTTP 200 and JSON body `{"status": "ok"}`.

#### Scenario: Healthz returns ok

- GIVEN the FastAPI app is running locally
- WHEN a client sends `GET /healthz`
- THEN the response status is 200
- AND the response body equals `{"status": "ok"}`
- AND the `Content-Type` header is `application/json`

### Requirement: App Factory With Lifespan Scaffold

`fragwise_api.main` MUST construct `app` via an app-factory pattern (a `create_app()` callable or equivalent) and MUST attach an `async def lifespan(app)` context manager. The lifespan body MAY be empty (no DB/Redis wiring in 0b) but the structure MUST be in place so later phases can plug startup/shutdown without refactor. Running `uvicorn fragwise_api.main:app` MUST start the app.

#### Scenario: App is importable and uvicorn-runnable

- GIVEN the api project has been installed via `uv sync`
- WHEN running `uv run uvicorn fragwise_api.main:app --host 127.0.0.1 --port 8000`
- THEN the process binds port 8000
- AND `GET /healthz` from another shell returns 200

### Requirement: LangGraph Stub Without Heavy ML Dependencies

`apps/api/src/fragwise_api/agent.py` MUST exist, MUST import `langgraph`, and MUST expose a compiled no-op graph (proves install + import shape). The dependency closure MUST NOT include `torch`, `transformers`, or `sentence-transformers`. Top-level `langchain` and `langchain-openai` MUST NOT be installed in 0c either. `langchain-core` MAY be present in the dependency tree as a transitive dependency of `langgraph` — this is acceptable and clarifies the W2 verify warning carried over from 0b.

#### Scenario: LangGraph stub imports cleanly

- GIVEN the api project has been installed
- WHEN running `uv run python -c "import fragwise_api.agent"`
- THEN the import succeeds with exit code 0
- AND `uv tree` output contains no entry for `torch`, `transformers`, `sentence-transformers`
- AND `uv tree` shows no top-level `langchain` or `langchain-openai` entry (transitive `langchain-core` under `langgraph` is allowed)

### Requirement: Test Infrastructure For Healthz

`apps/api/tests/test_health.py` MUST use `httpx.AsyncClient` (or FastAPI `TestClient`) to assert that `/healthz` returns HTTP 200 and JSON body `{"status": "ok"}`. `uv run pytest` MUST exit 0 from `apps/api/`.

#### Scenario: Pytest discovers and passes the health test

- GIVEN `apps/api/`
- WHEN running `uv run pytest`
- THEN pytest discovers at least one test
- AND every test passes
- AND the process exits 0

### Requirement: Lint And Type Tooling Pass

`apps/api/pyproject.toml` MUST configure `[tool.ruff]`, `[tool.mypy]` (with `strict = true` or equivalent), and `[tool.pytest.ini_options]`. `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src` MUST each exit 0 against the scaffolded code.

#### Scenario: Ruff and mypy are clean on scaffold

- GIVEN `apps/api/`
- WHEN running `uv run ruff check .` then `uv run mypy src`
- THEN both processes exit 0
- AND no errors are reported

### Requirement: Dockerfile Builds Runnable Image

`apps/api/Dockerfile` MUST exist and MUST produce a runnable image based on `python:3.12-slim` (or current stable `python:3.12-*` slim variant) using `uv sync` for dependency installation. The built image, when run, MUST serve `/healthz` returning 200.

#### Scenario: Image builds and serves healthz

- GIVEN `apps/api/Dockerfile`
- WHEN running `docker build -t fragwise-api apps/api` and `docker run -p 8000:8000 fragwise-api`
- THEN the build succeeds
- AND `GET http://localhost:8000/healthz` returns status 200 and body `{"status": "ok"}`

### Requirement: Database Session Lifecycle

The FastAPI app MUST construct an async SQLAlchemy engine and an `async_sessionmaker` on startup inside `lifespan(app)`, using the `DATABASE_URL` environment variable (asyncpg driver, e.g. `postgresql+asyncpg://...`). The engine MUST be stored on `app.state` (e.g. `app.state.db_engine`, `app.state.db_sessionmaker`) so request handlers and dependencies can access it. The engine MUST be disposed via `await engine.dispose()` on shutdown.

#### Scenario: Engine is constructed on startup and disposed on shutdown

- GIVEN `DATABASE_URL` is set and points at a reachable Postgres+pgvector DB
- WHEN the app starts via `uvicorn fragwise_api.main:app` and then receives SIGTERM
- THEN startup logs show an engine is constructed
- AND during runtime `app.state.db_engine` is a `sqlalchemy.ext.asyncio.AsyncEngine` instance
- AND on shutdown the engine is disposed (no leaked connections, verifiable via Postgres `pg_stat_activity`)

#### Scenario: Missing DATABASE_URL fails fast at startup

- GIVEN `DATABASE_URL` is unset in the environment
- WHEN the app attempts to start
- THEN startup raises an explicit error naming `DATABASE_URL`
- AND the process exits non-zero

### Requirement: Readiness Endpoint

`GET /readyz` MUST execute `SELECT 1` against the database via the lifespan-owned engine. On success it MUST return HTTP 200 with JSON body `{"status": "ready"}`. On any DB error (connection refused, query failure, timeout) it MUST return HTTP 503 with JSON body `{"status": "unready", "error": "<short message>"}`. `/healthz` (process up) and `/readyz` (DB reachable) MUST be distinct endpoints.

#### Scenario: Readyz returns 200 when DB is up

- GIVEN the app is running and Postgres is reachable
- WHEN a client sends `GET /readyz`
- THEN the response status is 200
- AND the response body equals `{"status": "ready"}`

#### Scenario: Readyz returns 503 when DB is unreachable

- GIVEN the app is running but Postgres is stopped (or `DATABASE_URL` points at an unreachable host)
- WHEN a client sends `GET /readyz`
- THEN the response status is 503
- AND the response body has shape `{"status": "unready", "error": "<message>"}`

#### Scenario: Healthz remains shallow and Readyz remains deep

- GIVEN the app is running and Postgres is stopped
- WHEN a client sends `GET /healthz` and then `GET /readyz`
- THEN `GET /healthz` returns 200 with `{"status": "ok"}`
- AND `GET /readyz` returns 503

### Requirement: Alembic Migration Applies Cleanly

Running `alembic upgrade head` against an empty Postgres+pgvector database MUST succeed. Running `alembic downgrade base` after an upgrade MUST also succeed and MUST produce an empty schema. Migrations MUST be invokable from `apps/api/` via `uv run alembic ...` (justfile recipe `just db-migrate`, `just db-rollback`, `just db-reset`).

#### Scenario: Upgrade then downgrade produces an empty schema

- GIVEN an empty Postgres+pgvector DB and `apps/api/` with the venv synced
- WHEN running `cd apps/api && uv run alembic upgrade head`
- THEN the command exits 0
- AND `\dt` in psql shows the project tables
- WHEN running `cd apps/api && uv run alembic downgrade base`
- THEN the command exits 0
- AND `\dt` in psql shows no project tables
- AND `SELECT extname FROM pg_extension WHERE extname='vector'` returns no rows

### Requirement: Ontology Loader Validates Files

`apps/api/src/fragwise_api/ontology/loader.py` MUST exist and MUST expose three callables: `load_notes() -> list[NoteRecord]`, `load_accords() -> list[AccordRecord]`, `load_synonyms() -> list[SynonymRecord]`. The loader MUST validate file structure via pydantic v2 models, MUST require a top-level `version: 1` field on every YAML/JSON file, and MUST raise a clear, informative error on invalid YAML/JSON, missing version, or unknown version values.

#### Scenario: Loader returns validated data on a valid ontology

- GIVEN `packages/ontology/notes.yaml`, `accords.yaml`, and `synonyms.json` are present and valid
- WHEN calling `load_notes()`, `load_accords()`, and `load_synonyms()`
- THEN each call returns a list of pydantic-validated record models
- AND no exceptions are raised

#### Scenario: Loader rejects a file missing the version field

- GIVEN `packages/ontology/notes.yaml` is present but its top-level `version` field has been removed
- WHEN calling `load_notes()`
- THEN the call raises an exception (pydantic `ValidationError` or `ValueError`) referencing the missing `version` field
- AND the message names the offending file path

#### Scenario: Loader rejects malformed YAML

- GIVEN `packages/ontology/accords.yaml` contains invalid YAML syntax
- WHEN calling `load_accords()`
- THEN the call raises an exception with a clear parse-error message
- AND the message identifies the file path
