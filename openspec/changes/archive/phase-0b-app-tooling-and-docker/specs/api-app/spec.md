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

`apps/api/src/fragwise_api/agent.py` MUST exist, MUST import `langgraph`, and MUST expose a compiled no-op graph (proves install + import shape). The dependency closure MUST NOT include `torch`, `transformers`, or `sentence-transformers`. `langchain` and `langchain-openai` MUST NOT be installed in 0b.

#### Scenario: LangGraph stub imports cleanly

- GIVEN the api project has been installed
- WHEN running `uv run python -c "import fragwise_api.agent"`
- THEN the import succeeds with exit code 0
- AND `uv tree` output contains no entry for `torch`, `transformers`, `sentence-transformers`, `langchain`, or `langchain-openai`

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
