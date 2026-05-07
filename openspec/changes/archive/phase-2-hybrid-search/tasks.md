# Tasks: Phase 2 — Hybrid Search

> **GATE — READ FIRST**: Phase 2 `sdd-apply` is BLOCKED until Phase 1
> (`phase-1-catalog-read-endpoints`) apply has merged. P2 imports
> `FragranceListItem` from `fragwise_api.api.v1.schemas.fragrance` (P1
> deliverable). If Task 1.1 fails, STOP and surface to the orchestrator —
> do not attempt to land any other task.

## Phase 1: Pre-flight

- [x] 1.1 Verify P1 apply landed: run `git log --oneline -- apps/api/src/fragwise_api/api/v1/schemas/fragrance.py` and `python -c "from fragwise_api.api.v1.schemas.fragrance import FragranceListItem"`. If either fails, BLOCK and report.

## Phase 2: Dependency updates

- [x] 2.1 Edit `apps/api/pyproject.toml` per `design.md §"File Changes"`: add `slowapi>=0.1.9,<1.0`, `redis>=5,<7`, bump `openai>=2.11,<3.0`, dev-add `fakeredis>=2.20,<3.0`. Run `uv lock` from `apps/api/` to regenerate `uv.lock`.

## Phase 3: Constants module + indexer refactor

- [x] 3.1 Create `apps/api/src/fragwise_api/search/__init__.py` (empty) and `apps/api/src/fragwise_api/search/constants.py` per `design.md §"constants.py"` (EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, EMBEDDING_VIEW, RRF_K, DEFAULT_HNSW_EF_SEARCH, DEFAULT_TOP_K, MAX_TOP_K, CACHE_NAMESPACE, CACHE_TTL_SECONDS).
- [x] 3.2 Refactor `data/scripts/embed_fragrances.py` to import `MODEL`/`DIMENSIONS`/`VIEW` from `fragwise_api.search.constants`. Re-run the indexer's existing smoke/unit test to confirm behavior unchanged.

## Phase 4: Search package modules

- [x] 4.1 Create `apps/api/src/fragwise_api/search/embedder.py` per `design.md`: `embed_query(text, client)` with tenacity `stop_after_attempt(3)` + `wait_exponential(min=1, max=8)` on `APIError`/`APITimeoutError`/`APIConnectionError`; let `asyncio.CancelledError` propagate.
- [x] 4.2 Create `apps/api/src/fragwise_api/search/retrieval.py` with `hybrid_retrieve(...)` and `fts_retrieve(...)` per `design.md §"Hybrid SQL"`: single SQLAlchemy `text()` round trip, `SET LOCAL hnsw.ef_search`, RRF fuse with `k=60`, filter pushdown, tie-break by `id ASC`.
- [x] 4.3 Create `apps/api/src/fragwise_api/search/cache.py` with `cache_key(req)`, `get_cached(redis, key)`, `set_cached(redis, key, value, ttl=86400)` per `design.md §"Cache key"`.
- [x] 4.4 Create `apps/api/src/fragwise_api/search/rate_limit.py` exposing `Limiter` factory bound to lifespan Redis URL and `search_rate_limit = limiter.limit("60/hour")` decorator.
- [x] 4.5 Create `apps/api/src/fragwise_api/search/daily_limit.py` with `increment_and_check(r, limit, now_utc)` (INCR + first-set EXPIRE to next UTC midnight + 60s), `peek_count(...)`, and `DailyLimitReached` exception per `design.md §"Daily-counter rollover"`.
- [x] 4.6 Create `apps/api/src/fragwise_api/search/fallback.py` with `fts_only_retrieval(...)` delegating to `retrieval.fts_retrieve` and tagging `match_reason`.
- [x] 4.7 Create `apps/api/src/fragwise_api/search/schemas.py` (pydantic v2): `FilterSpec`, `SearchRequest`, `SimilarRequest`, `SearchHit` (forward-ref `FragranceListItem` from P1), `SearchResponse` per `design.md §"schemas.py"`.
- [x] 4.8 Create `apps/api/src/fragwise_api/search/router.py`: `APIRouter(prefix="/api/v1")` with `POST /search` and `POST /fragrances/{slug}/similar`; wire `Annotated` deps for Session/Redis/AsyncOpenAI/Request; reuse P1's `api/v1/errors.py` envelope; 404 on unknown slug or missing embedding.

## Phase 5: Lifespan + router wiring

- [x] 5.1 Modify `apps/api/src/fragwise_api/main.py` lifespan per `design.md §"Lifespan diff"`: ADD `app.state.redis`, `app.state.openai_client`, `app.state.limiter`; ADD shutdown closes. Keep existing P0c DB engine/sessionmaker wiring untouched. Show diff in the apply summary.
- [x] 5.2 In `create_app()`: register `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)` and `app.include_router(search_router)`. Confirm `/api/v1/search` and `/api/v1/fragrances/{slug}/similar` show up in OpenAPI.

## Phase 6: Tests

- [x] 6.1 Create `apps/api/tests/integration/search/conftest.py` fixtures: testcontainers Postgres (reuse 0c), `import fakeredis.aioredis as fakeredis_async` then `fakeredis_async.FakeRedis()`, AsyncMock OpenAI returning a deterministic 512-dim embedding. Verify the fakeredis API in the installed version.
- [x] 6.2 Write happy + filtered tests: `test_search_happy.py` (hybrid 200, ranked, `match_reason` non-empty) and `test_search_filtered.py` (filter-pushdown invariant per spec scenario "Filter excludes the otherwise-top vector match").
- [x] 6.3 Write cache + fallback tests: `test_search_cache.py` (miss→hit, degraded never cached, daily counter unchanged on hit) and `test_search_fallback.py` (OpenAI APIConnectionError → 200 + `degraded=true`, FTS-only).
- [x] 6.4 Write rate-limit + similar + no-embeddings tests: `test_search_rate_limit.py` (60 OK / 61 → 429; use freezegun or slowapi reset utility — DO NOT sleep an hour), `test_similar.py` (200 without OpenAI call, 404 unknown slug, 404 missing embedding), `test_search_no_embeddings.py` (zero-embedding catalog still returns FTS+ontology).
- [x] 6.5 Write unit tests: `tests/unit/test_embedding_parity.py` (`idx.MODEL == q.EMBEDDING_MODEL`, dims, view), `tests/unit/test_cache_key.py` (filter-order normalization yields identical keys), `tests/unit/test_daily_limit.py` (INCR rollover + EXPIRE on first INCR via fakeredis).

## Phase 7: Justfile

- [x] 7.1 Edit `justfile` to add `redis-up` (docker run upstash/redis or redis:7-alpine on 6379), `redis-down`, `redis-shell` (`redis-cli`), and `search-bench` (stub: `echo "TODO: implement search bench"`).

## Phase 8: Self-check

- [x] 8.1 From `apps/api/`: `uv sync` exits clean; no resolver warnings.
- [x] 8.2 From repo root: `just test` (unit suite incl. parity, cache-key, daily-limit) is green.
- [x] 8.3 From repo root: `just test-integration` is green if Docker is available; specifically `pytest -m integration apps/api/tests/integration/search/` passes all 7 search tests.
