# Delta for api-app

## ADDED Requirements

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
