# Design: Phase 2 — Hybrid Search

## Technical Approach

A new `apps/api/src/fragwise_api/search/` package owns the hybrid retrieval pipeline. `POST /api/v1/search` and `POST /api/v1/fragrances/{slug}/similar` share the same retrieval module: vector + FTS + ontology fused via Reciprocal Rank Fusion (RRF, `k=60`) inside a single SQL CTE, with filters as predicates on the base CTEs (no Python-side merging). `AsyncOpenAI` and `redis.asyncio.Redis` are constructed once in `lifespan` and stored on `app.state`. slowapi (Redis-backed) enforces 60/hour per IP; a global UTC-day INCR counter is the kill-switch (503). OpenAI failures degrade to FTS-only with `degraded=true` (never 503). Exact-match cache only (`search:v1:{sha256(...)}`, 24h TTL); semantic cache deferred per ADR-0028.

## Architecture Decisions

| ID | Decision | Alternatives | Rationale |
|---|---|---|---|
| ADR-0026 | DB-side RRF in one SQL statement | Python-side merge; weighted score | One round trip, atomic snapshot, filter pushdown trivial; pgvector docs validate the recipe |
| ADR-0027 | Lifespan singletons for AsyncOpenAI + Redis on `app.state` | Per-request construction; module globals | Connection reuse, predictable lifecycle, mirrors existing engine pattern |
| ADR-0028 | Exact-match cache only | Add semantic cache | Simpler invariants, lower stale-result risk; revisit after telemetry |
| ADR-0029 | Fail-open with `degraded=true` for OpenAI outages | 503 with `Retry-After` | Better UX during OpenAI hiccups; chatbot (P3) keeps working; 503 reserved for kill-switch |
| ADR-0030 | fakeredis for Redis tests; testcontainers for Postgres only | testcontainers-redis everywhere | fakeredis is faster, no Docker dep for redis-only paths |
| ADR-0031 | Shared `search/constants.py` for `EMBEDDING_MODEL`/`EMBEDDING_DIMENSIONS`; indexer imports from it | Duplicate constants in two files | Equality test prevents silent drift |
| ADR-0032 | `SET LOCAL hnsw.ef_search = 100` (env-overridable) | Default 40 | Better recall@K at our catalog scale; transaction-scoped, no leak |

## Data Flow

    Client ─POST /search─▶ Router ──┐
                                    │
                  rate-limit ◀──────┤    [slowapi+Redis]
                  daily-counter ◀───┤    [Redis INCR/EXPIRE]
                  cache lookup ◀────┤    [Redis GET search:v1:{hash}]
                                    │
                       ┌────────────▼────────────┐
                       │ embedder (AsyncOpenAI)  │ ── retry (tenacity)
                       │  on failure → degraded  │
                       └────────────┬────────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │ retrieval.py (1 SQL)    │
                       │  SET LOCAL ef_search    │
                       │  vector CTE + FTS CTE   │
                       │  + ontology predicates  │
                       │  RRF fuse (k=60)        │
                       └────────────┬────────────┘
                                    ▼
                          response (+cache write
                          if not degraded)

`/fragrances/{slug}/similar` skips the embedder: it loads the source row's `embedding` from `fragrance_embeddings` and feeds the same retrieval module.

## File Changes

| File | Action | Description |
|---|---|---|
| `apps/api/src/fragwise_api/search/__init__.py` | Create | Package marker |
| `apps/api/src/fragwise_api/search/constants.py` | Create | `EMBEDDING_MODEL = "text-embedding-3-small"`, `EMBEDDING_DIMENSIONS = 512`, `EMBEDDING_VIEW = "combined"`, `RRF_K = 60`, `DEFAULT_HNSW_EF_SEARCH = 100` |
| `apps/api/src/fragwise_api/search/embedder.py` | Create | `embed_query(text, client)` with tenacity retry on `APIError`/`APITimeoutError`/`APIConnectionError` (`stop_after_attempt(3)`, `wait_exponential(min=1, max=8)`); re-raises after exhaustion; `asyncio.CancelledError` propagates unwrapped |
| `apps/api/src/fragwise_api/search/retrieval.py` | Create | `hybrid_retrieve(session, embedding, query_text, filters, top_k)` — RRF SQL CTE (see Interfaces). FTS-only path `fts_retrieve(...)` shares the filter-pushdown helper |
| `apps/api/src/fragwise_api/search/cache.py` | Create | `cache_key(req)`, `get_cached(redis, key)`, `set_cached(redis, key, value, ttl=86400)`; SHA256 over normalized JSON |
| `apps/api/src/fragwise_api/search/rate_limit.py` | Create | Module-level `Limiter` factory bound to lifespan-owned Redis URL; per-route decorator `search_rate_limit = limiter.limit("60/hour")` |
| `apps/api/src/fragwise_api/search/daily_limit.py` | Create | `increment_and_check(redis, limit, now_utc)` — `INCR search:dailycount:{YYYY-MM-DD}`; on first INCR (=1) sets `EXPIRE` to seconds-until-next-UTC-midnight + 60s; `peek_count(...)` for cache-hit path; raises `DailyLimitReached` |
| `apps/api/src/fragwise_api/search/fallback.py` | Create | `fts_only_retrieval(session, query_text, filters, top_k)` — calls `retrieval.fts_retrieve` and tags `match_reason=["fts"]`/`["ontology"]` |
| `apps/api/src/fragwise_api/search/schemas.py` | Create | pydantic v2: `SearchRequest`, `SimilarRequest`, `SearchHit`, `SearchResponse`. `SearchHit.fragrance: "FragranceListItem"` forward-ref imported from `fragwise_api.api.v1.schemas.fragrance` (P1 dep) |
| `apps/api/src/fragwise_api/search/router.py` | Create | `APIRouter(prefix="/api/v1")`; `POST /search` and `POST /fragrances/{slug}/similar`. Uses `Annotated` deps: `Session`, `Redis`, `AsyncOpenAI`, `Request` (for slowapi). Wires error envelope from `api/v1/errors.py` (P1) |
| `apps/api/src/fragwise_api/main.py` | Modify | Lifespan adds `AsyncOpenAI` + `redis.asyncio.Redis` to `app.state`; register `Limiter` and `_rate_limit_exceeded_handler`; mount `search.router.router` |
| `data/scripts/embed_fragrances.py` | Modify | Replace local `MODEL`/`DIMENSIONS`/`VIEW` constants with imports from `fragwise_api.search.constants` |
| `apps/api/pyproject.toml` | Modify | Add `slowapi>=0.1.9,<1.0`, `redis>=5,<7`; bump `openai>=2.11,<3.0`; dev: `fakeredis>=2.20,<3.0` |
| `apps/api/uv.lock` | Modify | Regenerate via `uv lock` |
| `apps/api/tests/integration/search/conftest.py` | Create | Fixtures: testcontainers Postgres (reuses 0c), `fakeredis.aioredis.FakeRedis`, AsyncOpenAI `AsyncMock` with deterministic embedding |
| `apps/api/tests/integration/search/test_search_happy.py` | Create | Hybrid 200 path |
| `apps/api/tests/integration/search/test_search_filtered.py` | Create | Filter pushdown invariant |
| `apps/api/tests/integration/search/test_search_cache.py` | Create | First miss, second hit; degraded never cached |
| `apps/api/tests/integration/search/test_search_fallback.py` | Create | OpenAI fails → 200 + `degraded=true` |
| `apps/api/tests/integration/search/test_search_rate_limit.py` | Create | 60 OK, 61 → 429 |
| `apps/api/tests/integration/search/test_similar.py` | Create | Slug found, no OpenAI call; 404 unknown slug; 404 missing embedding |
| `apps/api/tests/integration/search/test_search_no_embeddings.py` | Create | Catalog with zero embedding rows still returns FTS+ontology |
| `apps/api/tests/unit/test_embedding_parity.py` | Create | Asserts `embed_fragrances.MODEL == search.constants.EMBEDDING_MODEL` and dimensions equality |
| `apps/api/tests/unit/test_cache_key.py` | Create | Filter-order normalization yields identical keys |
| `apps/api/tests/unit/test_daily_limit.py` | Create | INCR rollover, EXPIRE on first INCR |
| `justfile` | Modify | Add `redis-up`, `redis-down`, `redis-shell`, `search-bench` (stub) |

## Interfaces / Contracts

### `search/constants.py`

```python
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 512
EMBEDDING_VIEW = "combined"
RRF_K = 60
DEFAULT_HNSW_EF_SEARCH = 100
DEFAULT_TOP_K = 20
MAX_TOP_K = 50
CACHE_NAMESPACE = "search:v1"
CACHE_TTL_SECONDS = 86400
```

### `search/schemas.py` (pydantic v2)

```python
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=512)
    filters: FilterSpec = Field(default_factory=FilterSpec)
    top_k: int = Field(default=20, ge=1, le=50)
    include: list[Literal["notes", "brand", "perfumer"]] = Field(default_factory=list)

class FilterSpec(BaseModel):
    gender: Literal["masculine","feminine","unisex"] | None = None
    accord: list[str] = Field(default_factory=list)
    brand: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    concentration: str | None = None
    note: list[str] = Field(default_factory=list)

class SearchHit(BaseModel):
    fragrance: "FragranceListItem"  # imported from fragwise_api.api.v1.schemas.fragrance (P1 dep)
    relevance_score: float = Field(ge=0.0, le=1.0)
    match_reason: list[Literal["vector","fts","ontology"]]

class SearchResponse(BaseModel):
    data: list[SearchHit]
    degraded: bool = False
    cache_hit: bool = False
```

### Hybrid SQL (parameterized via SQLAlchemy `text()`)

```sql
SET LOCAL hnsw.ef_search = :ef_search;
WITH filtered AS (
  SELECT f.id
  FROM fragrances f
  LEFT JOIN concentrations c ON c.id = f.concentration_id
  WHERE (:gender::fragrance_gender IS NULL OR f.gender = :gender::fragrance_gender)
    AND (:brand_slug::text IS NULL OR f.brand_id = (SELECT id FROM brands WHERE slug = :brand_slug))
    AND (:year_min::int IS NULL OR f.year_released >= :year_min)
    AND (:year_max::int IS NULL OR f.year_released <= :year_max)
    AND (:concentration_slug::text IS NULL OR c.slug = :concentration_slug)
    AND (:accord_slugs::text[] IS NULL OR EXISTS (
        SELECT 1 FROM fragrance_accords fa JOIN accords a ON a.id = fa.accord_id
        WHERE fa.fragrance_id = f.id AND a.slug = ANY(:accord_slugs)))
    AND (:note_slugs::text[] IS NULL OR EXISTS (
        SELECT 1 FROM fragrance_notes fn JOIN notes n ON n.id = fn.note_id
        WHERE fn.fragrance_id = f.id AND n.slug = ANY(:note_slugs)))
),
vector_cte AS (
  SELECT e.fragrance_id, ROW_NUMBER() OVER (ORDER BY e.embedding <=> :query_embedding) AS rank_v
  FROM fragrance_embeddings e
  JOIN filtered ff ON ff.id = e.fragrance_id
  WHERE e.view = :view AND e.model = :model AND e.dimensions = :dims
    AND :query_embedding::vector(512) IS NOT NULL
  ORDER BY e.embedding <=> :query_embedding
  LIMIT 100
),
fts_cte AS (
  SELECT f.id AS fragrance_id,
         ROW_NUMBER() OVER (
           ORDER BY ts_rank_cd(
             to_tsvector('english', f.name || ' ' || coalesce(f.description, '')),
             plainto_tsquery('english', :query_text)
           ) DESC
         ) AS rank_f
  FROM fragrances f
  JOIN filtered ff ON ff.id = f.id
  WHERE :query_text::text IS NOT NULL
    AND to_tsvector('english', f.name || ' ' || coalesce(f.description, ''))
        @@ plainto_tsquery('english', :query_text)
  LIMIT 100
)
SELECT COALESCE(v.fragrance_id, k.fragrance_id) AS fragrance_id,
       COALESCE(1.0/(:rrf_k + v.rank_v), 0)
     + COALESCE(1.0/(:rrf_k + k.rank_f), 0) AS rrf_score,
       (v.fragrance_id IS NOT NULL) AS hit_vector,
       (k.fragrance_id IS NOT NULL) AS hit_fts
FROM vector_cte v
FULL OUTER JOIN fts_cte k ON v.fragrance_id = k.fragrance_id
ORDER BY rrf_score DESC, COALESCE(v.fragrance_id, k.fragrance_id) ASC
LIMIT :top_k;
```

`relevance_score` is `min(1.0, rrf_score / (2.0/(:rrf_k+1)))` (normalize to [0,1] using max possible RRF score). `match_reason` is built from `hit_vector`/`hit_fts` plus an `"ontology"` tag whenever any ontology filter is active. The fallback path runs the same SQL with the vector CTE elided (or `query_embedding=NULL` short-circuit).

### Cache key

```python
def cache_key(req: SearchRequest) -> str:
    norm = {
        "query": req.query.strip().lower(),
        "filters": {
            "gender": req.filters.gender,
            "accord": sorted(req.filters.accord),
            "brand": req.filters.brand,
            "year_min": req.filters.year_min,
            "year_max": req.filters.year_max,
            "concentration": req.filters.concentration,
            "note": sorted(req.filters.note),
        },
        "top_k": req.top_k,
        "include": sorted(req.include),
    }
    return f"{CACHE_NAMESPACE}:{sha256(json.dumps(norm, sort_keys=True).encode()).hexdigest()}"
```

Write semantics: `if not response.degraded: await redis.set(key, response_json, ex=CACHE_TTL_SECONDS)`. Degraded path skips the SET entirely.

### Lifespan diff (apps/api/src/fragwise_api/main.py)

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = make_engine()
    app.state.db_engine = engine
    app.state.db_sessionmaker = make_sessionmaker(engine)

    redis_url = os.environ["REDIS_URL"]
    app.state.redis = redis.asyncio.Redis.from_url(redis_url, decode_responses=False)
    app.state.openai_client = AsyncOpenAI()  # picks up OPENAI_API_KEY

    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=redis_url,
        headers_enabled=True,
        in_memory_fallback_enabled=True,
        swallow_errors=True,
    )
    app.state.limiter = limiter
    try:
        yield
    finally:
        await app.state.openai_client.close()
        await app.state.redis.aclose()
        await engine.dispose()
```

`create_app` adds `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)` and `app.include_router(search_router)`.

### Daily-counter rollover

Key: `search:dailycount:{YYYY-MM-DD}` (UTC). Pseudocode:

```python
async def increment_and_check(r, limit, now_utc):
    key = f"search:dailycount:{now_utc.strftime('%Y-%m-%d')}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.ttl(key)
    new_count, ttl = await pipe.execute()
    if ttl < 0:  # first INCR of the day
        await r.expire(key, _seconds_until_next_utc_midnight(now_utc) + 60)
    if new_count > limit:
        raise DailyLimitReached()
```

Cache-hit path uses `peek_count(r, day_key)` — `GET` only, no INCR.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Cache key normalization; daily-limit math; embedding-parity | Pure pytest with `fakeredis.aioredis.FakeRedis`; no DB |
| Integration | Hybrid happy/filtered; cache hit/skip-on-degraded; rate-limit 429; daily 503; fallback `degraded=true`; similar (no OpenAI call); empty-embedding 404; no-embeddings catalog | testcontainers Postgres + fakeredis + AsyncMock OpenAI; arrange-act-assert; assertions match spec scenarios |
| Drift | `EMBEDDING_MODEL`/`EMBEDDING_DIMENSIONS` parity between indexer and query embedder | Direct import + `assert ==` |
| Manual/bench | `just search-bench` stub for future load testing | Recipe present, body `echo "TODO: implement search bench"` |

Embedding-parity test (exact code):

```python
def test_embedding_model_and_dims_match_indexer() -> None:
    from fragwise_api.search import constants as q
    from data.scripts import embed_fragrances as idx
    assert idx.MODEL == q.EMBEDDING_MODEL
    assert idx.DIMENSIONS == q.EMBEDDING_DIMENSIONS
    assert idx.VIEW == q.EMBEDDING_VIEW
```

## Migration / Rollout

No DB migration required (consumes 0c schema). Deploy order: Phase 1 router/schema landed → Phase 2 apply (sets `FragranceListItem` import). Env vars `OPENAI_API_KEY`, `REDIS_URL`, optional `FRAGWISE_HNSW_EF_SEARCH`, `FRAGWISE_SEARCH_RATE_PER_IP_HOUR`, `FRAGWISE_DAILY_SEARCH_LIMIT` already in `.env.example`. Rollback = revert merge; Redis cache flushes naturally.

## Cross-Cutting

- **Cancellation**: `embed_query` does not catch `asyncio.CancelledError`; client disconnect cancels the OpenAI call cleanly.
- **Rate-limit headers**: `Limiter(headers_enabled=True)` adds `X-RateLimit-*` and `Retry-After`; verify no middleware strips them.
- **Fly.io proxy**: uvicorn must run with `--forwarded-allow-ips '*'` for `get_remote_address` to see real client IP; documented as ops note.
- **Cache write skip**: handler captures `degraded` flag from retrieval result; only writes cache when `degraded is False`.
- **Process gate**: P2 `sdd-apply` is BLOCKED until P1 apply lands `FragranceListItem` in `fragwise_api.api.v1.schemas.fragrance`. Document in tasks.

## Open Questions

- [ ] Should `relevance_score` normalization use a fixed denominator (current proposal) or running max in the result set? Current: fixed for stability across requests.
- [ ] Should empty-result responses get the full 24h TTL or a shorter 5min TTL (per exploration §D)? Defer to operator env `FRAGWISE_CACHE_EMPTY_RESULTS` (default true, full TTL) per spec.
