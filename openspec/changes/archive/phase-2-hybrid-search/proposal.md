# Proposal: Phase 2 — Hybrid Search

## Intent

Phase 1 ships read-only catalog endpoints. Phase 2 layers semantic discovery on top: a hybrid (vector + FTS + ontology) search endpoint and a "more like this" endpoint, reusing the `fragrance_embeddings` table and HNSW/GIN indexes from 0c. The catalog becomes browsable by intent, not just by name, and the chatbot in Phase 3 has a retrieval primitive to call.

## Scope

### In Scope
- `POST /api/v1/search` — body `{query, filters?, top_k?, include?}`; returns `{data, degraded?, cache_hit?}`
- `POST /api/v1/fragrances/{slug}/similar` — same response shape; uses stored embedding (no OpenAI call)
- `apps/api/src/fragwise_api/search/`: `embedder.py`, `retrieval.py`, `cache.py`, `rate_limit.py`, `fallback.py`, schemas, ranking
- DB-side hybrid retrieval (RRF, single SQL) with filter pushdown; `SET LOCAL hnsw.ef_search = 100`
- Lifespan singletons: `AsyncOpenAI`, `redis.asyncio.Redis` (env-driven)
- Redis exact-match cache (`search:v1:{hash}`, 24h TTL)
- slowapi rate limit: per-IP 60/hr + 1000/day; daily global call counter as kill-switch
- Fail-open fallback: OpenAI failure → FTS-only with `degraded=true` (never 503)
- `justfile` recipes: `redis-up`, `redis-down`, `redis-shell`, `search-bench` stub
- Integration tests: happy, filtered, cache-hit, fallback, rate-limit, similar, no-embeddings
- Spec: `api-app` delta + new `search` capability

### Out of Scope
- LLM re-ranking (Phase 3)
- Semantic cache (fast-follow if hit-rate < 50%)
- Per-user rate limiting; analytics; spell correction; query expansion; autocomplete
- HNSW production tuning (separate observability change)

## Capabilities

### New Capabilities
- `search`: hybrid retrieval pipeline, exact-match cache, rate limiting, degraded-mode fallback

### Modified Capabilities
- `api-app`: adds Hybrid Search Endpoint, Similar Fragrances Endpoint, Search Cache Behavior, Search Rate Limiting, Search Degraded-Mode Fallback

## Approach

DB-side RRF (Context7-validated pgvector recipe) merges vector cosine + FTS `ts_rank` in one SQL with filters as predicates. AsyncOpenAI embeds the query (`text-embedding-3-small @ 512`); model + dim constants live in `search/embedder.py` mirroring `embed_fragrances.py`. slowapi+Redis enforces limits; fakeredis covers tests. `/similar` skips embedding by reading from `fragrance_embeddings`. Apply waits on Phase 1 routers/schemas being merged.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `apps/api/src/fragwise_api/search/` | New | retrieval pipeline modules |
| `apps/api/src/fragwise_api/main.py` | Modified | lifespan + router + limiter wiring |
| `apps/api/pyproject.toml` + `uv.lock` | Modified | add `slowapi`, `redis>=5,<7` |
| `apps/api/tests/integration/search/` | New | 7 integration tests |
| `justfile` | Modified | redis recipes + bench stub |
| `openspec/specs/api-app/spec.md` | Delta | 5 new requirements |
| `openspec/specs/search/spec.md` | New | new capability spec |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| OpenAI cost runaway | Med | 24h cache + daily kill-switch; semantic cache as fast-follow |
| Phase-1 route collision | Med | Phase 1 lands first; coordinate router mounts |
| Embedding-model drift | Med | Shared constants module + equality test |
| HNSW recall too low | Low | `ef_search=100` default; env override |
| OpenAI outage | Med | Fail-open with `degraded=true` |
| Rate-limit math wrong | Low | Explicit 429 test |

## Rollback Plan

Pre-merge: `git reset`. Post-merge pre-deploy: revert merge commit. Post-deploy: revert; no migrations to roll back (no schema changes); Redis cache flushes naturally as the app stops writing.

## Dependencies

- Phase 1 (`phase-1-catalog-read-endpoints`) merged before Phase 2 `sdd-apply` runs
- 0c embeddings populated in target environments
- `OPENAI_API_KEY` and `REDIS_URL` set (already in `.env.example` from 0a)

## Success Criteria

- [ ] `POST /search` returns ranked hybrid results with cache + rate limit
- [ ] `POST /fragrances/{slug}/similar` returns ranked results without an OpenAI call
- [ ] OpenAI outage → FTS-only response with `degraded=true`, never 503
- [ ] Per-IP rate limit returns 429 when exceeded
- [ ] All 7 integration tests pass against testcontainers Postgres + fakeredis
