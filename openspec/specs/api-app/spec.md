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

### Requirement: Catalog API Available Under /api/v1/

The 12 catalog read routes (defined in the `catalog-api` capability) MUST be mounted under the `/api/v1/` prefix via per-resource `APIRouter` instances. The existing `/healthz` and `/readyz` endpoints MUST remain at the repository root and MUST NOT be re-mounted under `/api/v1/`.

#### Scenario: Versioned routes mounted, health probes unversioned

- GIVEN the FastAPI app is running
- WHEN sending `GET /api/v1/fragrances`, `GET /api/v1/brands`, `GET /api/v1/perfumers`, `GET /api/v1/notes`, `GET /api/v1/accords`, `GET /api/v1/articles`
- THEN every request returns status 200 with a list-envelope body
- AND `GET /healthz` returns 200 with `{"status": "ok"}`
- AND `GET /readyz` returns 200 with `{"status": "ready"}`
- AND `GET /api/v1/healthz` returns 404

### Requirement: Static OpenAPI Emission

The repository MUST commit `apps/api/openapi.json`. An emit script (e.g. `apps/api/scripts/emit_openapi.py`) MUST exist that imports `fragwise_api.main:app`, calls `app.openapi()`, and writes the result to `apps/api/openapi.json` using deterministic JSON serialization (sorted keys, `(",", ":")` separators, UTF-8 with trailing newline). A `just emit-openapi` recipe MUST run the script. The CI workflow `.github/workflows/api.yml` MUST include a step that runs the emit script and fails if `git diff --exit-code apps/api/openapi.json` reports any changes.

The committed bytes of `apps/api/openapi.json` MUST equal the deterministic serialization of the live `app.openapi()` output.

#### Scenario: Emit script produces a deterministic file

- GIVEN the api project is installed
- WHEN running `cd apps/api && uv run python scripts/emit_openapi.py`
- THEN the script writes `apps/api/openapi.json` with sorted-keys deterministic JSON
- AND running the script a second time produces a byte-identical file (no diff)

#### Scenario: CI drift gate fails on stale file

- GIVEN `apps/api/openapi.json` is out of date relative to the live schema
- WHEN the `.github/workflows/api.yml` OpenAPI emission step runs
- THEN the step exits non-zero
- AND the workflow log indicates `apps/api/openapi.json` is stale and must be regenerated

#### Scenario: Live schema is byte-equal to the committed file

- GIVEN the committed `apps/api/openapi.json`
- WHEN computing `json.dumps(app.openapi(), sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"`
- THEN those bytes equal the bytes of the committed file

### Requirement: Hybrid Search Endpoint

`POST /api/v1/search` MUST accept a JSON body `{query: string (required, 1-512 chars), filters?: {gender?: "masculine"|"feminine"|"unisex", accord?: string[], brand?: string, year_min?: int, year_max?: int, concentration?: string, note?: string[]}, top_k?: int (1-50, default 20), include?: ("notes"|"brand"|"perfumer")[]}` and return `{data: [{fragrance: <list-shape>, relevance_score: float in [0,1], match_reason: string[]}], degraded: bool, cache_hit: bool}` on success. The endpoint MUST validate request shape with pydantic v2 and return 422 on invalid bodies. The endpoint MUST be subject to per-IP rate limiting (60/hour) and the daily kill-switch (see `Search Rate Limiting`). The endpoint MUST integrate the cache (see `Search Cache Behavior`) and the degraded-mode fallback (see `Search Degraded-Mode Fallback`). The `<list-shape>` of `fragrance` MUST match the existing `GET /api/v1/fragrances` list-item shape extended only by `include`-selected expansions.

#### Scenario: Happy path returns ranked hybrid results

- GIVEN the catalog is populated and OpenAI is reachable
- WHEN the client POSTs `{"query": "smoky leather", "top_k": 5}`
- THEN the response status is 200
- AND the body has `data` (length <= 5), `degraded: false`, and `cache_hit: false` on first call
- AND each `data[i]` has `relevance_score` in `[0,1]` and a non-empty `match_reason`

#### Scenario: Invalid request returns 422

- WHEN the client POSTs `{"query": ""}` (empty string) or `{"query": "x", "top_k": 999}`
- THEN the response status is 422
- AND the body identifies the offending field

#### Scenario: Rate limit returns 429

- GIVEN an IP that has consumed its hourly budget
- WHEN it issues another search
- THEN the response status is 429 with `{"error": {"code": "rate_limited", ...}}`

#### Scenario: Daily kill-switch returns 503

- GIVEN the daily counter has tripped
- WHEN any IP issues a non-cache-hit search
- THEN the response status is 503 with `{"error": {"code": "daily_limit_reached", ...}}`

#### Scenario: OpenAI outage degrades, does not 503

- GIVEN OpenAI is unreachable after retries
- WHEN a search request arrives
- THEN the response status is 200 with `degraded: true`
- AND the result set is FTS + ontology only

### Requirement: Similar Fragrances Endpoint

`POST /api/v1/fragrances/{slug}/similar` MUST accept `{top_k?: int (1-50, default 20), include?: ("notes"|"brand"|"perfumer")[]}` and return the same response shape as `POST /api/v1/search`. The handler MUST load the source fragrance's stored embedding from `fragrance_embeddings` and feed it directly into the retrieval pipeline; it MUST NOT call OpenAI for the source fragrance. The endpoint MUST share rate limiting and the daily kill-switch with `/search`. If `{slug}` does not match any fragrance, the response MUST be 404 with a clear error. If the fragrance exists but has no row in `fragrance_embeddings`, the response MUST be 404 with a message indicating the fragrance has no embedding (graceful degrade, not 500).

#### Scenario: Similar returns ranked results without an OpenAI call

- GIVEN fragrance with slug `creed-aventus` exists with a stored embedding
- WHEN the client POSTs `/api/v1/fragrances/creed-aventus/similar` with `{"top_k": 10}`
- THEN the response status is 200
- AND the body has the same envelope shape as `/search`
- AND `app.state.openai_client.embeddings.create` is NOT invoked

#### Scenario: Unknown slug returns 404

- WHEN the client POSTs `/api/v1/fragrances/does-not-exist/similar`
- THEN the response status is 404
- AND the body identifies the missing slug

#### Scenario: Source fragrance has no embedding returns 404

- GIVEN fragrance `legacy-fragrance` exists but has no row in `fragrance_embeddings`
- WHEN the client POSTs `/api/v1/fragrances/legacy-fragrance/similar`
- THEN the response status is 404
- AND the body's message identifies that the fragrance lacks an embedding

### Requirement: Search Cache Behavior

Successful, non-degraded responses from `POST /api/v1/search` MUST be cached in Redis under key `search:v1:{sha256(normalized_request_json)}` with TTL 24h. Normalization rules: query is lowercased and stripped; filter dict keys are sorted; filter list values are sorted lexically; `top_k` is included; `include` is sorted. Degraded responses MUST NOT be written to the cache. Cache hits MUST set `cache_hit: true` and MUST NOT increment the daily kill-switch counter. (Mirrors `search` capability: Cache Key Shape And Normalization, Cache Write Semantics.)

#### Scenario: Second identical request hits the cache

- GIVEN a successful non-degraded search response was just stored
- WHEN the same normalized request is reissued
- THEN the response body has `cache_hit: true`
- AND the daily counter is unchanged

#### Scenario: Degraded response is not cached

- GIVEN OpenAI is failing and a request returned `degraded: true`
- WHEN an identical request is reissued (still failing)
- THEN the response is recomputed (no cache hit)

### Requirement: Search Rate Limiting

The search endpoints MUST enforce per-IP `60/hour` via slowapi backed by Redis, returning 429 with `{"error": {"code": "rate_limited", "message": "..."}}` on overage. A global daily counter at `search:dailycount:YYYY-MM-DD` (UTC) MUST be checked at request entry; when it exceeds `FRAGWISE_DAILY_SEARCH_LIMIT` (default 5000), ALL search calls MUST return 503 with `{"error": {"code": "daily_limit_reached", "message": "..."}}` until the day rolls. Cache hits MUST NOT consume the daily budget. (Mirrors `search` capability: Per-IP Rate Limiting, Daily Kill-Switch.)

#### Scenario: 60th hourly request OK, 61st returns 429

- GIVEN an IP has issued 59 search requests in the last hour
- WHEN it issues request 60 (valid) then 61
- THEN request 60 returns 200
- AND request 61 returns 429

#### Scenario: Daily kill-switch trips and rolls

- GIVEN `FRAGWISE_DAILY_SEARCH_LIMIT=10` and the counter is at 10
- WHEN any IP issues a non-cache-hit search
- THEN the response is 503 with `code: "daily_limit_reached"`
- WHEN the UTC day rolls
- THEN search requests succeed again

### Requirement: Search Degraded-Mode Fallback

When `app.state.openai_client.embeddings.create(...)` fails after `tenacity` retries on `openai.APIError`, `openai.APITimeoutError`, or `openai.APIConnectionError`, the search pipeline MUST skip the vector branch and return FTS + ontology results with `degraded: true` in the response. The endpoint MUST NOT return 503 for OpenAI outages; 503 is reserved for the daily kill-switch. (Mirrors `search` capability: Fail-Open Degraded-Mode Fallback.)

#### Scenario: OpenAI outage degrades to FTS + ontology

- GIVEN OpenAI returns `APIConnectionError` for all retries
- WHEN a client POSTs to `/api/v1/search`
- THEN the response status is 200 with `degraded: true`
- AND the result set is derived from FTS + ontology only
- AND the response is not cached

#### Scenario: Daily kill-switch overrides OpenAI outage

- GIVEN OpenAI is failing AND the daily counter has tripped
- WHEN a client POSTs to `/api/v1/search`
- THEN the response status is 503 with `code: "daily_limit_reached"`

### Requirement: Chat Endpoint

`POST /api/v1/chat` MUST accept a JSON body `{messages: ChatMessage[], session_id?: string}` where `ChatMessage = {role: "user" | "assistant" | "system", content: string}` and respond with `Content-Type: text/event-stream` plus the header `X-Accel-Buffering: no` (to disable proxy buffering for self-hosters fronted by Nginx-class proxies). The handler MUST validate, before opening the SSE stream, that:

- `messages` is non-empty
- The last message's `role` is `"user"`
- Each `messages[i].content` is at most 4000 characters (cheap pre-check before the token-cap check)
- The `messages` array contains at most 20 entries (10 user + 10 assistant turns)

Validation failures MUST return HTTP 422 with the canonical envelope `{"error": {"code": "<code>", "message": "...", "detail": {...}}}` and MUST NOT open the SSE stream. On success, the response MUST stream events per the `agent` capability's SSE event schema and MUST terminate with a `done` event.

#### Scenario: Happy path opens SSE and terminates with done

- GIVEN a valid request body with `messages = [{role: "user", content: "smoky leather for winter"}]`
- WHEN the client POSTs `/api/v1/chat`
- THEN the response status is 200
- AND `Content-Type: text/event-stream` and `X-Accel-Buffering: no` headers are present
- AND the stream terminates with `event: done` carrying `finish_reason: "complete"`

#### Scenario: Empty messages array returns 422

- WHEN the client POSTs `{"messages": []}`
- THEN the response status is 422
- AND the body is `{"error": {"code": "invalid_request", ...}}`
- AND no SSE stream is opened

#### Scenario: Last message must be from the user

- WHEN the client POSTs `{"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]}`
- THEN the response status is 422
- AND the body's `error.code` is `"invalid_request"`
- AND no SSE stream is opened

#### Scenario: Per-message content length cap

- WHEN any `messages[i].content` exceeds 4000 characters
- THEN the response status is 422
- AND the body's `error.code` is `"invalid_request"` with detail naming the offending index

### Requirement: Chat Rate Limiting

The chat endpoint MUST enforce per-IP slowapi rate limits backed by the existing P2 Redis singleton: `5 requests / 1 hour` AND `20 requests / 1 day`, evaluated concurrently as separate windows. Limits MUST be configurable via env `FRAGWISE_CHAT_RATE_PER_IP_HOUR` (default 5) and `FRAGWISE_CHAT_RATE_PER_IP_DAY` (default 20). When EITHER threshold is exceeded the handler MUST return HTTP 429 with body `{"error": {"code": "rate_limited", "message": "..."}}` and MUST NOT open the SSE stream.

#### Scenario: 5th hourly request OK, 6th returns 429

- GIVEN an IP has issued 4 chat requests in the last hour
- WHEN it issues request 5 (valid) then 6
- THEN request 5 returns 200 with an SSE stream
- AND request 6 returns 429 with `error.code = "rate_limited"`
- AND request 6 never opens an SSE stream

#### Scenario: Daily window also enforced

- GIVEN an IP has issued 20 chat requests in the last 24 hours
- WHEN it issues request 21
- THEN the response status is 429
- AND `error.code = "rate_limited"`

#### Scenario: Window resets

- GIVEN an IP has been 429'd
- WHEN both windows have rolled past their earliest counted requests
- THEN a valid request returns 200

### Requirement: Chat Daily Kill-Switch

A global daily counter at Redis key `chat:dailycount:YYYY-MM-DD` (UTC) MUST be incremented on each chat call (including ones that ultimately error inside the stream). When the counter exceeds `FRAGWISE_DAILY_CHAT_LIMIT` (default 200), ALL chat calls MUST return HTTP 503 with body `{"error": {"code": "daily_limit_reached", "message": "..."}}` and MUST NOT open the SSE stream until the next UTC day. The first INCR of a new day MUST set EXPIRE to (next UTC midnight) + 60s buffer to ensure clean rollover. 503 MUST be reserved exclusively for the daily kill-switch; OpenAI outages MUST NOT produce 503.

#### Scenario: 201st call returns 503

- GIVEN `FRAGWISE_DAILY_CHAT_LIMIT=200` and the day's counter is at 200
- WHEN any IP issues a chat request
- THEN the response status is 503 with `error.code = "daily_limit_reached"`
- AND no SSE stream is opened

#### Scenario: Counter rolls at UTC midnight

- GIVEN the daily counter has tripped on day D
- WHEN the UTC clock crosses midnight into day D+1
- THEN a fresh `chat:dailycount:<D+1>` key starts at 0
- AND chat requests succeed again

#### Scenario: First INCR of the day sets EXPIRE

- GIVEN today's `chat:dailycount:YYYY-MM-DD` does not yet exist in Redis
- WHEN the first chat request of the day is processed
- THEN the key is INCR'd to 1
- AND TTL is set to `(seconds until next UTC midnight) + 60`

### Requirement: Chat Conversation Length Cap

The chat handler MUST enforce a hard cap of 20 messages per request (10 user-assistant turn pairs), configurable via `FRAGWISE_CHAT_MAX_TURNS` (default 10 turns = 20 messages). The check MUST run BEFORE the SSE stream is opened. Overflow MUST return HTTP 422 with body `{"error": {"code": "conversation_too_long", "message": "...", "detail": {"max_messages": 20}}}`.

#### Scenario: 20 messages OK, 21 returns 422

- GIVEN a request with `messages` length 20 (valid)
- WHEN the client POSTs the request
- THEN the response status is 200 with an SSE stream
- WHEN the client POSTs a request with `messages` length 21
- THEN the response status is 422
- AND `error.code = "conversation_too_long"` with `detail.max_messages = 20`
- AND no SSE stream is opened

### Requirement: Chat Message Token Cap

Each `ChatMessage.content` MUST be tokenized via `tiktoken` for the `gpt-4o-mini` encoder. If any message's token count exceeds 1000 (configurable via `FRAGWISE_CHAT_MAX_USER_TOKENS`, default 1000), the request MUST be REJECTED (not truncated) with HTTP 422 and body `{"error": {"code": "message_too_long", "message": "...", "detail": {"max_tokens": 1000}}}`. The check MUST run before the SSE stream is opened.

#### Scenario: 1000-token message OK, 1001 returns 422

- GIVEN a `ChatMessage.content` whose tiktoken count for `gpt-4o-mini` is exactly 1000
- WHEN the client POSTs the request
- THEN the response status is 200
- WHEN the same request is reissued with content totaling 1001 tokens
- THEN the response status is 422
- AND `error.code = "message_too_long"` with `detail.max_tokens = 1000`
- AND no SSE stream is opened
- AND the message is NOT silently truncated

### Requirement: Chat Degraded-Mode Fallback

OpenAI failures inside the agent MUST degrade per-node, NEVER 503. The handler MUST emit fallbacks as follows:

- **Intake/clarify/rank failure**: emit a `degraded` SSE event naming the failing node (`reason: "openai_intake_failed"` / `"openai_clarify_failed"` / `"openai_rank_failed"`), then fall through to a generic clarify question (intake/clarify path) or to top-1 candidate without rank-reordering (rank path), then `done` with `finish_reason: "degraded"`.
- **Retrieve embedding failure**: the retrieve node's wrapper MUST fall through to FTS-only retrieval (mirrors P2 search degraded-mode); if the wrapper falls through, emit a `degraded` event with `reason: "openai_embedding_failed"` and continue the graph normally; the final `done` MUST report `finish_reason: "complete"` (the request still produced grounded picks).
- **Explain failure**: emit a `degraded` event with `reason: "openai_explain_failed"` naming the top-1 candidate (no reasoning), then `done` with `finish_reason: "degraded"`.

503 MUST be reserved exclusively for the daily kill-switch (see `Chat Daily Kill-Switch`). OpenAI outages MUST NEVER produce 503.

#### Scenario: Intake failure degrades to generic clarify

- GIVEN OpenAI fails for the intake node after retries
- WHEN a chat request runs
- THEN a `degraded` event with `reason: "openai_intake_failed"` is emitted
- AND a generic `clarify` event follows
- AND `done` reports `finish_reason: "degraded"`
- AND the response status is 200 (NOT 503)

#### Scenario: Retrieve embedding failure falls through to FTS

- GIVEN OpenAI embedding fails after retries but the chat-completion path is healthy
- WHEN a chat request runs
- THEN a `degraded` event with `reason: "openai_embedding_failed"` is emitted
- AND retrieve uses FTS + ontology only
- AND rank and explain still run normally
- AND `done` reports `finish_reason: "complete"`

#### Scenario: Explain failure degrades to top-1 without reasoning

- GIVEN OpenAI fails specifically for the explain node after retries
- WHEN a chat request runs
- THEN a `degraded` event with `reason: "openai_explain_failed"` is emitted naming the top-1 candidate
- AND no `recommendation` events follow
- AND `done` reports `finish_reason: "degraded"`
- AND the response status is 200 (NOT 503)

#### Scenario: 503 is reserved for daily kill-switch

- GIVEN OpenAI is unreachable for every retry on every node
- AND the daily kill-switch has NOT tripped
- WHEN a chat request runs
- THEN the response status is 200 with degraded events
- AND the response status is NEVER 503 due to OpenAI outage
