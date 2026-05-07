# catalog-api Specification

## Purpose

Defines the read-only public catalog HTTP surface: 12 endpoints (list + detail × 6 resources — fragrances, brands, perfumers, notes, accords, articles) mounted under `/api/v1/`. Locks API conventions (envelope, pagination, filters, errors, slugs, eager-loading) so downstream consumers (Phase 4 web app, Phase 3 chatbot tool layer) can rely on a stable contract.

## Requirements

### Requirement: API Version Prefix

All catalog routes MUST be mounted under `/api/v1/`. Health probes (`/healthz`, `/readyz`) MUST remain at root and MUST NOT be versioned.

#### Scenario: Versioned mount

- GIVEN the FastAPI app is running
- WHEN `GET /api/v1/fragrances` is sent
- THEN status is 200
- AND `GET /fragrances` (without prefix) returns 404

### Requirement: Trailing Slash Policy

`FastAPI` MUST be constructed with `redirect_slashes=False`. All routes MUST be declared without a trailing slash. A request to a path with a trailing slash MUST return 404 (not 307).

#### Scenario: Trailing slash returns 404

- GIVEN the app is running
- WHEN `GET /api/v1/fragrances/` is sent
- THEN status is 404
- AND no `Location` redirect header is present

### Requirement: Pagination Envelope

Every list endpoint MUST wrap results in `{"data": [...], "pagination": {"limit": int, "offset": int, "total": int, "has_next": bool}}`. `total` is the unfiltered-by-pagination count of matched rows; `has_next` is `true` iff `offset + limit < total`.

#### Scenario: Envelope shape on a populated list

- GIVEN at least 25 fragrances exist
- WHEN `GET /api/v1/fragrances?limit=20&offset=0` is sent
- THEN body has keys `data` (array length 20) and `pagination`
- AND `pagination` has integer `limit=20`, `offset=0`, `total>=25`, and `has_next=true`

#### Scenario: Offset beyond total returns empty data with correct total

- GIVEN exactly 5 brands exist
- WHEN `GET /api/v1/brands?offset=100&limit=20` is sent
- THEN status is 200
- AND `data` is `[]`
- AND `pagination.total` is 5 and `has_next` is `false`

### Requirement: Pagination Parameters

`?limit=` MUST default to 20, MUST validate as integer in `[1, 100]`, and out-of-range values MUST yield 422. `?offset=` MUST default to 0, MUST validate as integer `>= 0`, and negative values MUST yield 422.

#### Scenario: Invalid limit rejected

- GIVEN the app is running
- WHEN `GET /api/v1/fragrances?limit=500` is sent
- THEN status is 422
- AND error body uses the standard error envelope

#### Scenario: Negative offset rejected

- GIVEN the app is running
- WHEN `GET /api/v1/brands?offset=-1` is sent
- THEN status is 422

### Requirement: Error Envelope

All non-2xx responses MUST use the shape `{"error": {"code": string, "message": string, "detail": object|array|null}}`. Missing-slug detail endpoints MUST return 404; query-param validation failures MUST return 422.

#### Scenario: 404 on unknown slug

- GIVEN no brand with slug `does-not-exist` exists
- WHEN `GET /api/v1/brands/does-not-exist` is sent
- THEN status is 404
- AND body matches `{"error": {"code": "not_found", "message": <str>, "detail": ...}}`

#### Scenario: 422 on bad query

- GIVEN the app is running
- WHEN `GET /api/v1/fragrances?year_min=abc` is sent
- THEN status is 422
- AND body matches the error envelope shape

### Requirement: Multi-Value Filter OR Semantics

Repeated query keys MUST combine with OR semantics within a key. Different keys MUST combine with AND.

#### Scenario: OR within accord, AND across keys

- GIVEN fragrance A is tagged `floral` only, B tagged `woody` only, C tagged neither, all of brand `chanel`; D is `floral` of brand `dior`
- WHEN `GET /api/v1/fragrances?accord=floral&accord=woody&brand=chanel` is sent
- THEN `data` includes A and B but NOT C and NOT D

### Requirement: Slug-Based Identifiers

URL path identifiers MUST be slugs (`/api/v1/fragrances/aventus`). Filter values referencing other entities MUST be slugs (`?brand=chanel`, `?accord=floral`). UUID-based filters (`?brand_id=`) MUST NOT be accepted.

#### Scenario: Slug filter resolves

- GIVEN brand `chanel` has 3 fragrances
- WHEN `GET /api/v1/fragrances?brand=chanel` is sent
- THEN `pagination.total` equals 3
- AND `GET /api/v1/fragrances?brand_id=<uuid>` returns 422 (unknown query parameter or rejected by schema)

### Requirement: GET /api/v1/fragrances — List

Returns a paginated list of fragrances. Supported filters: `brand` (slug), `perfumer` (slug, multi), `gender` (enum), `year_min` (int), `year_max` (int), `concentration` (slug), `accord` (slug, multi), `note` (slug, multi). Each item MUST have shape `{id, slug, name, brand: {slug, name}, year_released, gender, concentration: {slug, name}|null}`. Default sort: `name ASC`.

#### Scenario: List with brand and gender filter

- GIVEN brand `chanel` has 3 fragrances of gender `fem` and 1 of gender `masc`
- WHEN `GET /api/v1/fragrances?brand=chanel&gender=fem` is sent
- THEN status is 200
- AND `data` length is 3
- AND every item's `brand.slug` is `chanel` and `gender` is `fem`
- AND items are sorted by `name` ascending

### Requirement: GET /api/v1/fragrances/{slug} — Detail

Returns the full fragrance object with nested `brand` (object), `perfumers` (array), `notes` grouped by role as `{top: [], heart: [], base: []}`, `accords` (array), `articles` (array), `description`, `year_text`. 404 on unknown slug.

#### Scenario: Detail returns nested objects

- GIVEN fragrance `aventus` exists with brand, 2 perfumers, top/heart/base notes, 1 accord, 0 articles
- WHEN `GET /api/v1/fragrances/aventus` is sent
- THEN status is 200
- AND body has nested `brand`, `perfumers` (length 2), `notes.top`, `notes.heart`, `notes.base` arrays, `accords` (length 1), `articles` ([])

#### Scenario: 404 for unknown fragrance slug

- GIVEN no fragrance with slug `nope` exists
- WHEN `GET /api/v1/fragrances/nope` is sent
- THEN status is 404 with the error envelope

### Requirement: GET /api/v1/brands — List

Paginated list of brands. Supports optional `?q=` substring filter on `name` (case-insensitive). Items MUST have shape `{slug, name}`.

#### Scenario: List filtered by q

- GIVEN brands `chanel`, `chloe`, `dior` exist
- WHEN `GET /api/v1/brands?q=ch` is sent
- THEN `data` contains exactly the entries for `chanel` and `chloe`

### Requirement: GET /api/v1/brands/{slug} — Detail

Returns the brand `{slug, name}` plus a paginated `fragrances` array using the same envelope shape (`{data, pagination}`). 404 on unknown slug.

#### Scenario: Brand detail with paginated fragrances

- GIVEN brand `chanel` has 25 fragrances
- WHEN `GET /api/v1/brands/chanel?limit=10` is sent
- THEN status is 200
- AND body has top-level `slug`, `name`
- AND `fragrances.data` length is 10 and `fragrances.pagination.total` is 25

### Requirement: GET /api/v1/perfumers — List

Paginated list of perfumers with optional `?q=` substring filter on `name`. Items MUST have shape `{slug, name}`.

#### Scenario: Perfumers list with q filter

- GIVEN perfumers `jean-claude-ellena` and `francis-kurkdjian` exist
- WHEN `GET /api/v1/perfumers?q=jean` is sent
- THEN `data` includes the entry for `jean-claude-ellena`

### Requirement: GET /api/v1/perfumers/{slug} — Detail

Returns the perfumer plus a paginated `fragrances` array of fragrances they composed. 404 on unknown slug.

#### Scenario: Perfumer detail returns their fragrances

- GIVEN perfumer `jean-claude-ellena` has 5 fragrances
- WHEN `GET /api/v1/perfumers/jean-claude-ellena` is sent
- THEN body has `slug`, `name`, `fragrances.data` (length 5), `fragrances.pagination.total=5`

### Requirement: GET /api/v1/notes — Tree

Returns the full notes hierarchy as a tree. Response shape: `{data: [{slug, name, children: [...]}, ...]}`. No pagination; the response MUST be cacheable.

#### Scenario: Tree includes parent and children

- GIVEN parent note `citrus` has child `bergamot`
- WHEN `GET /api/v1/notes` is sent
- THEN status is 200
- AND `data` includes a node with `slug=citrus` whose `children` includes `{slug: "bergamot", ...}`

### Requirement: GET /api/v1/notes/{slug} — Detail

Returns the single note `{slug, name, parent: {slug, name}|null}` plus a paginated `fragrances` array of fragrances that include this note (any role). 404 on unknown slug.

#### Scenario: Note detail with fragrances

- GIVEN note `bergamot` is used in 12 fragrances
- WHEN `GET /api/v1/notes/bergamot?limit=5` is sent
- THEN status is 200
- AND `fragrances.data` length is 5 and `fragrances.pagination.total` is 12

### Requirement: GET /api/v1/accords — List

Returns a flat list of all accord families. Response shape: `{data: [{slug, name}, ...]}`. No pagination.

#### Scenario: All seeded accords returned

- GIVEN the seed loaded the six required accord families
- WHEN `GET /api/v1/accords` is sent
- THEN status is 200
- AND `data` length is at least 6
- AND every item has `slug` and `name`

### Requirement: GET /api/v1/accords/{slug} — Detail

Returns a single accord `{slug, name}` plus a paginated `fragrances` array of fragrances tagged with this accord. 404 on unknown slug.

#### Scenario: Accord detail with paginated fragrances

- GIVEN accord `floral` is tagged on 8 fragrances
- WHEN `GET /api/v1/accords/floral?limit=4` is sent
- THEN status is 200
- AND `fragrances.data` length is 4 and `fragrances.pagination.total` is 8

### Requirement: GET /api/v1/articles — List

Paginated list of articles. Items shape: `{slug, title, published_at}`.

#### Scenario: Articles list paginates

- GIVEN 30 articles exist
- WHEN `GET /api/v1/articles?limit=10&offset=10` is sent
- THEN status is 200
- AND `data` length is 10
- AND `pagination.total=30`, `offset=10`, `has_next=true`

### Requirement: GET /api/v1/articles/{slug} — Detail

Returns a single article `{slug, title, body, published_at, fragrances: [...]}`. 404 on unknown slug.

#### Scenario: Article detail returns body

- GIVEN article `top-10-summer` exists
- WHEN `GET /api/v1/articles/top-10-summer` is sent
- THEN status is 200
- AND body has non-empty `title`, `body`, `published_at`

### Requirement: N+1 Prevention On Fragrance Detail

`GET /api/v1/fragrances/{slug}` MUST execute no more than 6 SELECT statements total against the database (fragrance row + brand/concentration joinload counts as 1; perfumers; fragrance_notes-with-note; accords; articles; up to 1 reserved for future selectinload). Compliance MUST be verified by an integration test that asserts the query count.

#### Scenario: Query count is bounded

- GIVEN a fragrance `aventus` exists with brand, perfumers, notes, accords, articles populated
- WHEN the integration test instruments the AsyncSession and issues `GET /api/v1/fragrances/aventus`
- THEN the captured SELECT count is `<= 6`
- AND the response body still satisfies the detail-shape requirement

### Requirement: Eager Loading Strategy

The implementation MUST use `selectinload` for collection relationships (`Fragrance.notes`, `Fragrance.perfumers`, `Fragrance.accords`, `Fragrance.articles`) and `joinedload` for to-one relationships (`Fragrance.brand`, `Fragrance.concentration`). Lazy I/O on the async session MUST NOT occur during response serialization.

#### Scenario: No lazy load during serialization

- GIVEN the AsyncSession is configured with `expire_on_commit=False`
- WHEN serializing the fragrance detail response
- THEN no `MissingGreenlet` or implicit IO error is raised
- AND every nested relationship is preloaded by the eager strategy

### Requirement: OpenAPI Emission Available At Versioned Path

The FastAPI-generated OpenAPI schema MUST be served at `/api/v1/openapi.json`. The bytes of the served schema (after deterministic JSON serialization with sorted keys and a fixed separator) MUST be byte-equal to the committed `apps/api/openapi.json` file.

#### Scenario: Live schema matches committed file

- GIVEN the committed `apps/api/openapi.json`
- WHEN computing the deterministic serialization of the live `app.openapi()` output
- THEN the bytes equal the bytes of the committed file

### Requirement: CORS On Catalog Routes

The application MUST enable CORS for the `/api/v1/*` route subtree using FastAPI's CORS middleware. The allowed origin MUST be read from the environment variable `NEXT_PUBLIC_API_URL` (or `CORS_ALLOW_ORIGIN`); when unset in development, the origin MAY default to `*`.

#### Scenario: Preflight succeeds for the configured origin

- GIVEN `NEXT_PUBLIC_API_URL=https://fragwise.app` is set
- WHEN an `OPTIONS /api/v1/fragrances` request is made with `Origin: https://fragwise.app`
- THEN status is 200 (or 204)
- AND `Access-Control-Allow-Origin: https://fragwise.app` is present in the response headers
