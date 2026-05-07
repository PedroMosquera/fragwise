# search Specification

## Purpose

Defines the hybrid retrieval pipeline (pgvector + Postgres FTS + ontology filters with Reciprocal Rank Fusion), Redis-backed exact-match cache, per-IP and global rate limiting, and fail-open degraded-mode fallback that powers `POST /api/v1/search` and `POST /api/v1/fragrances/{slug}/similar`.

## Requirements

### Requirement: Hybrid Retrieval Pipeline

`apps/api/src/fragwise_api/search/retrieval.py` MUST execute hybrid retrieval as a single SQL statement (or a coordinated CTE set in one round trip) that combines pgvector cosine similarity (`<=>`), Postgres FTS `ts_rank`, and ontology predicates, ranking results via Reciprocal Rank Fusion with constant `k=60`. Inputs MUST be `(query_embedding: list[float] | None, filters: FilterSpec, top_k: int)`; output MUST be a list of `(fragrance_id, relevance_score: float in [0,1], match_reason: list[str])` where `match_reason` is the non-empty subset of `["vector", "fts", "ontology"]` indicating which signals contributed.

#### Scenario: Hybrid query returns RRF-ranked candidates

- GIVEN a query embedding, no filters, and `top_k=20`
- WHEN `retrieval.search(...)` is invoked
- THEN exactly one DB round trip runs (vector + FTS + ontology CTEs fused via RRF)
- AND the response contains up to 20 candidates ordered by descending `relevance_score`
- AND every candidate has a non-empty `match_reason` drawn from `{"vector", "fts", "ontology"}`

### Requirement: Filter Pushdown Invariant

Filters (gender, accord, brand, year range, concentration, note) MUST be applied as SQL predicates on the base CTEs, NOT post-retrieval in Python. The pipeline MUST NOT fetch unfiltered top-K and trim afterward.

#### Scenario: Filter excludes the otherwise-top vector match

- GIVEN fragrance A is the closest vector neighbor for the query but has `gender='masculine'`
- AND fragrance B is the second-closest neighbor with `gender='feminine'`
- WHEN `retrieval.search(query_embedding=..., filters={"gender": "feminine"}, top_k=5)` runs
- THEN the result set MUST NOT contain A
- AND B MUST appear at rank 1
- AND total returned rows MUST equal `min(5, count_of_matches)`

### Requirement: HNSW Runtime Tuning

The retrieval pipeline MUST execute `SET LOCAL hnsw.ef_search = 100` (or the value of `FRAGWISE_HNSW_EF_SEARCH` if set) before each vector search query, scoped to the transaction. The default 100 trades a small latency cost for materially higher recall@K vs the pgvector default of 40 on catalogs in the 10K-50K row range.

#### Scenario: ef_search is set per query

- GIVEN a search request that includes a vector branch
- WHEN the SQL is issued
- THEN `SET LOCAL hnsw.ef_search = <configured>` is executed in the same transaction before the `SELECT` using `<=>`
- AND the setting does NOT leak across transactions

### Requirement: Embedding Model Parity

Query-time embeddings MUST use the same model and dimension count as index-time. The constants `EMBEDDING_MODEL = "text-embedding-3-small"` and `EMBEDDING_DIMENSIONS = 512` MUST live in a single shared module imported by both `data/scripts/embed_fragrances.py` and `apps/api/src/fragwise_api/search/embedder.py`. An integration test MUST assert byte-for-byte equality of the constants between the two import sites.

#### Scenario: Drift test fails if constants diverge

- GIVEN the shared constants module
- WHEN the parity test imports both `embed_fragrances` and `search.embedder`
- THEN both expose `EMBEDDING_MODEL == "text-embedding-3-small"` and `EMBEDDING_DIMENSIONS == 512`
- AND the test fails loudly if either side is changed without the other

### Requirement: AsyncOpenAI Singleton Lifecycle

A single `openai.AsyncOpenAI` client MUST be constructed in the FastAPI `lifespan` startup phase, stored on `app.state.openai_client`, and closed on shutdown. Per-request handlers MUST reuse this singleton; constructing a new client per request is forbidden.

#### Scenario: Client is created once and disposed on shutdown

- GIVEN the app is starting
- WHEN `lifespan` enters
- THEN `app.state.openai_client` is an `AsyncOpenAI` instance
- WHEN the app receives SIGTERM
- THEN `await app.state.openai_client.close()` is invoked exactly once

### Requirement: Redis Singleton Lifecycle

A single `redis.asyncio.Redis` client (or backing connection pool) MUST be constructed in `lifespan` from `REDIS_URL`, stored on `app.state.redis`, and closed on shutdown. All cache, rate-limit, and kill-switch operations MUST use this singleton.

#### Scenario: Redis client is created once and closed on shutdown

- GIVEN `REDIS_URL` is set
- WHEN `lifespan` enters
- THEN `app.state.redis` is a `redis.asyncio.Redis` instance
- WHEN the app receives SIGTERM
- THEN `await app.state.redis.aclose()` (or pool.disconnect) is invoked exactly once

### Requirement: Cache Key Shape And Normalization

The exact-match cache key MUST be `search:v1:{sha256(normalized_request_json)}` where `normalized_request_json` is the canonical JSON encoding of: `{query: <lowercased+stripped>, filters: <dict with sorted keys; list values sorted lexically>, top_k: <int>, include: <sorted list>}`. TTL MUST be 24 hours (86400 seconds). The `v1` namespace allows future schema bumps via `v2`.

#### Scenario: Two requests differing only by filter ordering hit the same key

- GIVEN request A `{query: "Aventus", filters: {"accord": ["smoky","fruity"]}, top_k: 20, include: []}`
- AND request B `{query: "  aventus  ", filters: {"accord": ["fruity","smoky"]}, top_k: 20, include: []}`
- WHEN both requests' cache keys are computed
- THEN they MUST be identical
- AND the second request MUST observe `cache_hit: true`

#### Scenario: TTL is 24 hours

- GIVEN a successful non-degraded search response
- WHEN the response is written to Redis
- THEN the SET command MUST include `ex=86400`

### Requirement: Cache Write Semantics

ONLY successful, non-degraded responses MUST be written to the cache. Responses with `degraded: true` MUST NOT be cached. Responses with empty result sets MAY be cached at the same TTL (operator's choice via `FRAGWISE_CACHE_EMPTY_RESULTS`, default true).

#### Scenario: Degraded response is not cached

- GIVEN OpenAI is unavailable and the pipeline returns a `degraded: true` response
- WHEN the search handler completes
- THEN no Redis SET against `search:v1:*` is issued for that response
- AND a subsequent identical request MUST recompute (and may itself succeed non-degraded once OpenAI recovers)

### Requirement: Per-IP Rate Limiting

The search endpoints MUST be protected by `slowapi` with Redis storage at `60 requests / 1 hour` per remote IP. Exceeding the limit MUST return HTTP 429 with body `{"error": {"code": "rate_limited", "message": "..."}}`. The window MUST be a sliding/rolling hour anchored on the slowapi default semantics. Limits MUST be configurable via env `FRAGWISE_SEARCH_RATE_PER_IP_HOUR`.

#### Scenario: Just-under-limit succeeds

- GIVEN an IP has issued 59 search requests in the last hour
- WHEN the IP issues request 60
- THEN the response status MUST be 200 (assuming valid request)

#### Scenario: Just-over-limit returns 429

- GIVEN an IP has issued 60 search requests in the last hour
- WHEN the IP issues request 61
- THEN the response status MUST be 429
- AND the body MUST equal `{"error": {"code": "rate_limited", "message": "..."}}`

#### Scenario: Window resets

- GIVEN an IP has been 429'd at minute T
- WHEN the IP retries after the slowapi window has rolled past its earliest counted request
- THEN a valid request MUST again return 200

### Requirement: Daily Kill-Switch

A global daily counter at Redis key `search:dailycount:YYYY-MM-DD` (UTC) MUST be incremented on each non-cache-hit search call. When the counter exceeds `FRAGWISE_DAILY_SEARCH_LIMIT` (default 5000), ALL search calls MUST return HTTP 503 with body `{"error": {"code": "daily_limit_reached", "message": "..."}}` until the next UTC day. Cache hits MUST NOT increment the counter.

#### Scenario: Counter trips and rolls

- GIVEN `FRAGWISE_DAILY_SEARCH_LIMIT=10` and the day's counter is at 10
- WHEN any IP issues a fresh (non-cache-hit) search request
- THEN the response status MUST be 503
- AND the body MUST equal `{"error": {"code": "daily_limit_reached", "message": "..."}}`
- WHEN the UTC day rolls
- THEN a fresh `search:dailycount:<new-day>` key starts at 0
- AND requests succeed again

#### Scenario: Cache hit does not consume kill-switch budget

- GIVEN a cached response exists for request R
- WHEN R is issued
- THEN the daily counter is unchanged
- AND the response status is 200 with `cache_hit: true`

### Requirement: Fail-Open Degraded-Mode Fallback

When `app.state.openai_client.embeddings.create(...)` fails after the configured `tenacity` retries (on `openai.APIError`, `openai.APITimeoutError`, or `openai.APIConnectionError`), the pipeline MUST skip the vector branch, run FTS + ontology only with the same filter pushdown, and return the result set with `degraded: true` in the response envelope. The pipeline MUST NOT return HTTP 503 for OpenAI outages; 503 is reserved for the daily kill-switch.

#### Scenario: OpenAI outage degrades, never 503s

- GIVEN OpenAI returns `APIConnectionError` for every retry
- WHEN a search request arrives
- THEN the response status MUST be 200
- AND the response body MUST include `degraded: true`
- AND the result set MUST be derived from FTS + ontology only
- AND the response MUST NOT be cached

#### Scenario: Daily kill-switch still 503s during OpenAI outage

- GIVEN OpenAI is failing AND the daily counter has tripped
- WHEN a search request arrives
- THEN the response status MUST be 503 with `code: "daily_limit_reached"`

### Requirement: Ranking Stability

Identical requests issued against an unchanged corpus MUST return the same ranking in the same order. Ties in `relevance_score` MUST be broken deterministically by ascending `fragrances.id`.

#### Scenario: Repeated request returns identical ordering

- GIVEN the corpus is unchanged
- WHEN the same `(query, filters, top_k, include)` is issued twice (cache disabled)
- THEN the two response result lists MUST be byte-identical in `[fragrance_id, relevance_score, match_reason]` order
- AND any tie in `relevance_score` MUST be resolved by `id ASC`
