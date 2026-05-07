# Exploration: phase-2-hybrid-search

## Current State

After phase-0c, the API has the data + ML scaffolding to make hybrid retrieval cheap to bolt on:

- **Schema**. `fragrance_embeddings` already has `vector(512)` + HNSW (`vector_cosine_ops`,
  `m=16`, `ef_construction=64`). `fragrances` has GIN-FTS on
  `to_tsvector('english', name || ' ' || coalesce(description, ''))`. Joins exist
  for `fragrance_notes` (with `role`), `fragrance_perfumers`, plus the `accords`,
  `notes`, `concentrations` lookups. ENUM `fragrance_gender` is in place.
- **Embedding pipeline**. `data/scripts/embed_fragrances.py` already calls
  `text-embedding-3-small` with `dimensions=512` and uses `tenacity` for retry.
  The same `_build_canonical_text(...)` used at indexing time is the contract any
  query-time embedder should mirror conceptually (queries are *not* fragrance
  descriptions, but the same model + dimensions MUST match).
- **Lifespan**. `main.py::lifespan` already constructs the async engine + sessionmaker
  on `app.state`. Adding two more singletons (Redis, AsyncOpenAI) on the same
  `app.state` is the canonical extension point — no refactor required.
- **No HTTP listing/search yet**. Phase 1 (`phase-1-catalog-read-endpoints`) is
  in flight in parallel and will land `/fragrances` (list + detail). Phase 2 must
  not collide on the URL space.
- **No Redis client, no rate limiter, no slowapi dep yet**. Adding them is a phase-2
  decision; they are not listed in `apps/api/pyproject.toml` today.

## Affected Areas

- `apps/api/src/fragwise_api/main.py` — extend lifespan (Redis + AsyncOpenAI singletons), register routers, register slowapi limiter and exception handler.
- `apps/api/src/fragwise_api/api/` (new package) — `search.py` router for `POST /search`; optionally `similar.py` for `POST /fragrances/{slug}/similar` (depends on split decision).
- `apps/api/src/fragwise_api/search/` (new package) — pure logic split out of the router:
  - `embedder.py` — single-call wrapper around `AsyncOpenAI.embeddings.create(model='text-embedding-3-small', dimensions=512)`, tenacity-wrapped, swappable for tests via a Protocol.
  - `retrieval.py` — SQL builder for hybrid query (vector + FTS + filter pushdown + RRF).
  - `cache.py` — exact-match + semantic cache helpers around redis.
  - `schemas.py` — pydantic request/response models.
  - `ranking.py` — RRF combiner (fallback path when DB-side RRF is not used).
- `apps/api/src/fragwise_api/db/session.py` — no change expected; sessionmaker reused.
- `apps/api/src/fragwise_api/db/models/embedding.py` and `fragrance.py` — read-only consumers.
- `apps/api/pyproject.toml` — add `slowapi`, `redis>=5,<7` (asyncio); `aiohttp` optional if we adopt `DefaultAioHttpClient`.
- `apps/api/tests/` — unit tests with stubbed embedder + fakeredis; integration tests reuse the testcontainers fixture from 0c plus a fixture-fixed embedding for determinism.
- `apps/api/Dockerfile` / Fly secrets — needs `OPENAI_API_KEY`, `REDIS_URL`, daily token cap env at runtime (operator concern, not code).
- `data/scripts/embed_fragrances.py` — no change. Phase 2 only *consumes* embeddings written here.
- `openspec/specs/api-app/spec.md` — delta will add `POST /search` (and possibly `POST /fragrances/{slug}/similar`), rate-limit requirements, cache contract, `degraded` response field. (Phase 1's delta should land the listing endpoints; phase 2 must not stomp on it — coordinate via the proposal.)
- `openspec/specs/data-model/spec.md` — no schema change required. Optionally add a non-binding note that 512-dim vectors + HNSW with `vector_cosine_ops` is the contract Phase 2 reads against.

## Versions Verified Via Context7 (2026-05-06)

| Package | Pin proposal | Notes |
|---|---|---|
| `pgvector` (PG extension) | unchanged from 0c | `SET LOCAL hnsw.ef_search = N` is the canonical per-query knob (default 40). Iterative scans available in 0.8.0+ if needed for filtered queries with low recall. |
| `pgvector` (Python) | `>=0.4,<1.0` (already pinned) | `Vector(512)` + `<=>` cosine operator in raw SQL. |
| `openai` | `>=2.11,<3.0` (bump from `>=1.55`) | `AsyncOpenAI` documented in v2.x; `DefaultAioHttpClient` for aiohttp transport (optional). `embeddings.create(model='text-embedding-3-small', input=[...], dimensions=512)` confirmed. Built-in `max_retries`, `timeout` kwargs; per-request `with_options(...)`. Error types: `APITimeoutError`, `APIConnectionError`, `RateLimitError`, `APIStatusError`. |
| `slowapi` | `>=0.1.9,<1.0` | `Limiter(key_func=get_remote_address, storage_uri='redis://...')`, `app.state.limiter = limiter`, `_rate_limit_exceeded_handler`. Per-route `@limiter.limit("60/hour")` and `@limiter.limit("1000/day")` chain works. Custom `key_func` available if we later move to per-user. |
| `redis` (Python) | `>=5,<7` | `redis.asyncio.from_url('redis://...')` or `ConnectionPool.from_url(...)` then `redis.asyncio.Redis(connection_pool=...)`. `set(key, val, ex=ttl_seconds)` is the idiomatic write. |
| `tenacity` | unchanged (`>=9,<10`) | already a dep. Reuse the embed script's exponential-backoff pattern. |

Context7 also confirmed pgvector ships an end-to-end **hybrid-search RRF SQL example**
combining `<=>` cosine vector ranking with `ts_rank_cd` FTS ranking via
`FULL OUTER JOIN` and the standard `1.0/(60+rank)` RRF formula — see "Approaches"
below. This is a strong endorsement of doing RRF in SQL, not in Python.

## Approaches

### A. Endpoint shape

1. **`POST /search`** with body `{query, filters, top_k, include}` — recommended.
   - Pros: filters are structured; body hashes cleanly into a cache key; we can
     accept long natural-language queries without URL length issues; chatbot
     (phase 3) will call this internally.
   - Cons: not as RESTful as a `GET` listing; can't be bookmarked.
   - Effort: Medium.

2. **Extend phase-1's `GET /fragrances?q=...`** — defer to phase 1's listing and overload it.
   - Pros: one endpoint to learn.
   - Cons: filter shape balloons in query strings; URL-length limits hit fast;
     conflates "browse the catalog" (cheap, FTS-only) with "semantic search"
     (expensive, OpenAI call). Hard to put different rate limits on the same
     route.
   - Effort: Low (free-rides on phase 1) but bad design.

3. **Both**: `GET /fragrances?q=...` (FTS-only, cheap, shares phase-1 ratelimit) + `POST /search` (full hybrid, tighter ratelimit).
   - Pros: cheapest path stays cheap; expensive path is well-scoped.
   - Cons: two code paths; duplicated filter logic.
   - Effort: Medium.

**Recommendation**: **A** for phase 2. If phase 1 already adds a trivial `?q=` to
`/fragrances`, that's complementary, not in scope here. Phase 2 owns POST /search.

### B. "More like this" entrypoint

1. **`POST /fragrances/{slug}/similar`** — body `{top_k, filters}`. Internally
   pulls the fragrance's `embedding` from `fragrance_embeddings` and runs the
   same retrieval pipeline, skipping the OpenAI call entirely.
   - Pros: free (no OpenAI), high product value, almost free implementation
     (it's the same retrieval module with a different seed).
   - Cons: another route to spec + test.
   - Effort: Low.

2. **Defer to a later phase**.
   - Pros: smaller phase 2.
   - Cons: leaves obvious low-hanging fruit on the table; chatbot in phase 3 will
     want it for "I liked X, find me others".

**Recommendation**: include `POST /fragrances/{slug}/similar` in phase 2 since the
internals are 95% shared. See split recommendation at end.

### C. Hybrid recipe

1. **DB-side RRF** in a single SQL statement (per Context7's pgvector example).
   - Pros: filter pushdown is trivial (filters become predicates on the base
     CTEs); pagination is correct; one round trip; `EXPLAIN`-friendly; uses HNSW
     and GIN indexes; no Python-side rank merging.
   - Cons: weights are not tunable (RRF k=60 is the standard); SQL is denser.
   - Effort: Medium.

2. **Python-side weighted score combination**. Pull top-K from each retriever
   separately, then merge with `score = w_v*sim + w_f*ts_rank + w_o*overlap`.
   - Pros: weights tunable per-query (e.g., heavy ontology weight when filters
     match strongly).
   - Cons: two round trips OR a UNION-ALL with two sub-queries; weights are an
     opinion machine — every change is litigation; filter pushdown still
     required at the SQL layer (we don't gain anything in exchange for the
     extra knobs).
   - Effort: Medium-High (more code, more knobs to tune, more tests).

3. **Hybrid: DB-side RRF as default; expose an internal `?strategy=weighted`
   parameter for experimentation**.
   - Pros: production stays simple; we keep an escape hatch.
   - Cons: two code paths to maintain.
   - Effort: Medium-High.

**Recommendation**: **1** (DB-side RRF). Parameter-free, validated by pgvector's
own documentation. Tune later only if real usage proves a need. Document the
RRF constant `k=60` and that ontology overlap (notes/accords) participates as a
**hard filter** (predicate), not as a third score signal — this avoids the
weight-tuning trap and keeps filter pushdown clean.

### D. Caching strategy

1. **Exact-match cache only**. Hash `{normalized_query, sorted_filters, top_k}`,
   store JSON response in Redis under `search:v1:{hash}`, TTL ~24h.
   - Pros: deterministic, easy to reason about, easy to invalidate (bump
     namespace `v1`→`v2`), no extra index data structure.
   - Cons: minor query variations ("aventus" vs "aventus by creed") miss the
     cache → another OpenAI call.

2. **Exact-match + semantic cache**. Also store the query's embedding under
   `search:emb:{hash}`. On miss, scan the last N (e.g., 200) embeddings and reuse
   the response if cosine sim ≥ 0.92.
   - Pros: cuts OpenAI costs further on near-duplicate queries.
   - Cons: extra Redis ops per request; bounded scan size; risk of returning a
     "close but not quite" response (false-positive cache hits); requires a
     second data structure (sorted set / list of recent embeddings).
   - Mitigation: only do semantic-cache lookup when `filters` is empty (text-only
     queries are the duplication-prone case); cap candidate list at 100; pick a
     conservative threshold (≥0.95) initially.

3. **No cache**. Every call hits OpenAI.
   - Pros: trivial to ship.
   - Cons: cost runaway; chatbot in phase 3 will hammer this.

**Recommendation**: **start with 1 (exact-match)** to ship phase 2 fast, and
add **2 (semantic)** in the same phase only if implementation budget allows.
Wire the cache key namespace `search:v1:` from day one so versioning is free.
Log `cache_hit` boolean on every response (debug header, not body) so we can
measure hit rate before adding semantic cache. TTL: 24h for hits with non-empty
results; 5min for empty-result responses (so a typo doesn't poison the cache for
a day).

### E. Rate limiting

1. **Per-IP + global ceilings via slowapi + Redis**.
   - `@limiter.limit("60/hour")` and `@limiter.limit("1000/day")` per route, key
     by `get_remote_address`.
   - Plus a per-instance daily token-spend kill switch implemented as a Redis
     INCRBY counter (`spend:YYYY-MM-DD`) checked at the top of `POST /search`.
     If counter > cap (e.g., 250000 calls/day at $1/day budget), respond 503 with
     `{"status":"degraded","reason":"daily_cap"}`.
   - Pros: Context7 confirms slowapi is the right tool; redis is already needed
     for caching, so backend cost is amortized.
   - Cons: `get_remote_address` behind Fly.io needs `X-Forwarded-For` handling.
     slowapi has `get_ipaddr` for that, but operator must set
     `proxy_headers=True` on uvicorn or use `--forwarded-allow-ips`.

2. **No rate limit, rely on OpenAI's own quota**.
   - Pros: simplest.
   - Cons: a single curl-loop attacker drains the daily budget in minutes;
     OpenAI's rate-limit error returns 429 to the user but already burns money.

**Recommendation**: **1**. Document the IP-resolution caveat behind Fly's proxy.
Default per-IP: 60/hr + 1000/day. Default daily instance cap: 250000 calls
(~$1/day at $0.000004/call for `text-embedding-3-small@512`). Cap and per-IP
defaults MUST be env-overridable (`SEARCH_RATE_PER_IP_HOUR`,
`SEARCH_DAILY_CALL_CAP`) so operators tune per deployment.

### F. OpenAI failure mode

1. **Fail-open with FTS-only fallback**, response includes
   `degraded: true, degraded_reason: "embedder_unavailable"`.
   - Pros: catalog stays browsable; users still get *something*. Maps cleanly to
     a kill-switch test.
   - Cons: silent quality drop; clients should display a banner.

2. **Fail-closed (503)** with `Retry-After`.
   - Pros: clean failure mode; clients can't paper over a degraded service.
   - Cons: chatbot (phase 3) breaks completely if OpenAI hiccups.

**Recommendation**: **1**. Wire the `degraded` field from day one even when not
degraded (always present, just `false` in the happy path) — schema stability
matters once phase 3's chatbot consumes it. The fallback path is mechanical:
drop the vector CTE, run FTS-only with the same filter pushdown.

### G. HNSW query-time tuning

- Default `hnsw.ef_search = 40` is OK for small catalogs but recall drops fast at
  K beyond ~30. For our 50K-fragrance ceiling, recommend `SET LOCAL
  hnsw.ef_search = 100` per request (Context7-documented pattern). Make the
  number env-overridable (`SEARCH_HNSW_EF_SEARCH`).
- We're approximate by design; for 50K rows, recall@20 with ef_search=100 is
  effectively indistinguishable from exact for this product.
- Iterative scans (`SET hnsw.iterative_scan = relaxed_order`) are pgvector
  ≥0.8.0; flag as a future tuning option if filter selectivity is high enough
  that vanilla HNSW returns too few rows post-filter. Don't enable by default.

### H. Re-ranking deferral

Phase 2 does **NOT** include LLM re-ranking. Phase 3's chatbot is the natural
place: the agent will call `/search` for a candidate set, then optionally
re-rank inside its own LangGraph flow. Document this boundary in the proposal so
nobody accidentally adds a `?rerank=true` flag in phase 2.

## Recommendation

Ship a single phase that lands:

1. `POST /search` with body `{query, filters, top_k, include}`, response shape
   `{results: [{slug, name, brand, relevance_score, match_reason}], degraded:
   false, cache_hit: false}`. `match_reason` is a string tag — `"vector"`,
   `"fts"`, `"both"`, `"vector_only_filtered"` — derived from which CTE
   contributed the row in the RRF query.
2. `POST /fragrances/{slug}/similar` with body `{top_k, filters}` reusing the
   same retrieval pipeline, seeded by the source fragrance's embedding (no
   OpenAI call).
3. Lifespan-owned `AsyncOpenAI` and `redis.asyncio.Redis` singletons on
   `app.state`.
4. Exact-match cache with `search:v1:{hash}` keys and 24h TTL. (Semantic cache
   deferred to a fast-follow if cost data justifies it.)
5. Rate limiting: per-IP `60/hour` + `1000/day` via slowapi+Redis, plus a
   daily call counter as a hard kill-switch (returns 503 with `degraded`).
6. OpenAI fail-open → FTS-only fallback with `degraded: true`.
7. Hybrid retrieval as a single SQL statement using RRF (Context7's pgvector
   recipe), with `SET LOCAL hnsw.ef_search = 100` and filters as predicates on
   the base CTEs.
8. Tests: unit tests with a stub embedder (fixture-fixed vector) and fakeredis;
   integration tests use the existing testcontainers fixture and seed a small
   set of fragrances + embeddings.

### Split recommendation

Keep **unified** (single phase) instead of 2a/2b. Reasons:

- The retrieval module is identical between `/search` and `/fragrances/{slug}/similar`;
  splitting forces a half-baked first phase.
- Caching, rate-limiting, lifespan wiring, and observability are paid once for
  both endpoints — splitting doubles the proposal/spec/design overhead.
- The "+similar" endpoint is high-leverage (no OpenAI cost) and the
  chatbot phase wants it.

If implementation time pressure appears during sdd-tasks, a clean trim is to
ship `/similar` behind a feature flag while keeping it on the spec — but the
spec/design work happens in this phase regardless.

## Risks

- **Cost runaway**. Cache misses cost OpenAI tokens. Mitigations: 24h TTL,
  daily call counter kill-switch, monitor `cache_hit` rate, plan semantic-cache
  fast-follow if hit rate < 50%.
- **Cold start**. First query of the day after TTL = full retrieval. Acceptable
  given the `~$0.000004/call` cost; document don't fix.
- **HNSW recall regression**. `ef_search` too low → bad results. Default to 100,
  expose env override, write a test that asserts recall on a fixture set.
- **OpenAI outage**. Fail-open with FTS-only + `degraded: true` keeps the site
  alive. A future client banner reads the flag.
- **Embedder rate-limits at OpenAI**. `tenacity` exponential backoff (the
  embed_fragrances.py pattern) plus AsyncOpenAI's built-in `max_retries=2`
  covers transient 429s.
- **Cache stampede on cold start**. Many users hitting the same query at TTL
  expiry → N OpenAI calls. Mitigation: deferred — flag for phase 2.5 if
  observed; classic single-flight lock in Redis is the fix.
- **IP-resolution behind Fly.io's proxy**. `get_remote_address` returns the
  proxy IP unless uvicorn is configured with `--forwarded-allow-ips`. Document
  in the proposal; verify in the design.
- **Filter selectivity collapses HNSW**. If a user passes very narrow filters
  (one brand, one note), HNSW may return zero post-filter rows. Mitigation:
  iterative scans (`relaxed_order`) is a documented escape hatch; phase-2
  default behavior is to return the empty set with `match_reason: "no_match"` —
  not to silently widen the filters.
- **Phase-1 collision on `/fragrances/...`**. Phase-1 owns the listing route.
  Phase-2 adds `POST /fragrances/{slug}/similar` *under* phase-1's resource
  prefix. Coordinate ordering: phase-1 lands first, phase-2 layers on top.
  Worst case: phase-2 ships only `POST /search` if phase-1 is delayed.
- **Embedding-model drift**. If we ever change indexing model (`text-embedding-3-small`
  @ 512), query-time embedder MUST stay in lockstep. Encode the model + dims as
  module-level constants in `search/embedder.py`, mirrored from
  `embed_fragrances.py`'s constants — and add a test that asserts equality.

## Ready for Proposal

**Yes**. The orchestrator should:

1. Confirm phase-1 is sequenced first (hybrid-search depends on the catalog
   models + at least the listing endpoint pattern being in main).
2. Confirm the unified scope (search + similar) is acceptable; if a smaller
   first slice is preferred, drop `/similar` and call it phase 2a (deferred
   `/similar` to phase 2b).
3. Confirm the `degraded` fail-open default is acceptable product policy
   (vs strict 503).
4. Greenlight `slowapi` + `redis-py` as new deps (no other phase has added
   these yet).

After those four confirmations, run `sdd-propose` for `phase-2-hybrid-search`.
