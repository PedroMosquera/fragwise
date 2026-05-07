# Exploration: phase-1-catalog-read-endpoints

> Investigation only — no code, no design files. The orchestrator picks the
> recommendations to lock into `proposal.md`/`design.md`.

## Current State (post 0a/0b/0c)

- FastAPI app factory at `apps/api/src/fragwise_api/main.py` exposes
  `/healthz` and `/readyz` only. Lifespan owns an async SQLAlchemy engine
  and an `async_sessionmaker` on `app.state`. There is a
  `get_session(request)` FastAPI dependency in `db/session.py` (yields
  `AsyncSession`).
- 11 ORM models exist under `apps/api/src/fragwise_api/db/models/` with
  UUID v7 PKs, slugs (UNIQUE B-tree), `TimestampMixin`, PG ENUMs for
  `gender` and `note_role`, the `concentration` lookup, the note hierarchy
  (self-FK `parent_id`), the M:M joins, and the `fragrance_embeddings`
  table.
- DB session FK relationships defined so far:
  - `Fragrance.brand` (one-to-many backref `Brand.fragrances`)
  - `Fragrance.concentration` (no backref)
  - **No** ORM `relationship()` declared for `Fragrance.notes`,
    `Fragrance.perfumers`, `Fragrance.articles`, `Note.parent`, or any
    accord linkage. These are reachable only via explicit JOIN selects
    against the join tables today. **Phase 1 will need to add the
    missing `relationship()` declarations** (or use explicit selects per
    request) to support nested responses.
- **No accord ↔ fragrance link exists.** The schema seeded `accords`
  (chypre/fougere/oriental/gourmand/aquatic/woody) but there is no
  `fragrance_accords` join table or a derived view. The brief says
  `GET /accords/{slug}` returns paginated fragrances tagged with this
  accord — that data does not exist yet.

  → **This is a hard gap.** Phase 1 cannot ship a `fragrance_accords`
  endpoint without first deciding how accords attach to fragrances:
  (a) author-supplied via the seed YAML + new `fragrance_accords` join,
  or (b) derived from notes via ontology mapping, or (c) drop accord-
  filtered endpoints from Phase 1.

- No API routers, no schemas, no `/api/v1` prefix, no tags, no
  `openapi.json` export, no rate limiting, no caching middleware.
  FastAPI 0.128 default `/docs` and `/openapi.json` are live.
- pyproject pins are FastAPI `>=0.128`, SQLAlchemy `>=2.0.40`, pydantic
  `>=2.10`. All three support the modern patterns (`Annotated[..., Query]`,
  `selectinload` on `AsyncSession`, pydantic v2 `model_config`).

## Affected Areas

- `apps/api/src/fragwise_api/main.py` — register routers, add
  `openapi_tags`, decide on `/api/v1` prefix.
- `apps/api/src/fragwise_api/api/` — **new directory tree** for routers
  and schemas (does not exist yet).
- `apps/api/src/fragwise_api/db/models/*.py` — likely add `relationship()`
  declarations (notes/perfumers/articles, optional accords).
- `apps/api/src/fragwise_api/db/repositories/` (or `queries/`) — **new**
  if we extract query helpers; otherwise inline in routers.
- `apps/api/tests/integration/` — extend with per-router test files.
- `apps/web/` — downstream consumer; locks in once we ship.
- `openspec/specs/api-app/spec.md` — needs new requirements for the
  read-only API surface.
- A potential **new** capability spec `openspec/specs/catalog-api/`
  would scope cleaner than overloading `api-app`.

## Open Questions / Trade-offs (the asks)

### 1. Pagination strategy

| Option | Pros | Cons |
|---|---|---|
| **Offset + limit** (`?limit=20&offset=40`) | Trivial; matches FastAPI tutorial; debuggable; supports random-access UI | Deep pages (`offset=10000`) get slow with large catalogs; not stable under writes |
| **Cursor** (`?cursor=opaque`, response: `next_cursor`) | Fast at any depth; stable under writes | Opaque to humans; harder to "jump to page 50"; client must re-fetch from start to navigate backwards |
| **page+per_page** (`?page=3&per_page=20`) | Familiar to UI devs | Just offset in disguise — same deep-page perf cliff |

**Recommendation: offset+limit.** Catalog is <50K fragrances; even page
500 is a 10K offset, which is fast on an indexed `ORDER BY year_released
DESC, slug ASC`. The shape leaves a clean migration path to cursor: keep
`offset`/`limit` but later add `cursor` as an alternative. **Default
limit 20, max 100, validated via `Annotated[int, Query(ge=1, le=100)]`.**

### 2. Response shape

| Option | Pros | Cons |
|---|---|---|
| **Fully nested** (fragrance includes brand, perfumer[], notes-by-role, articles inline) | One round-trip; UI gets everything for a detail page; matches OpenAPI documentation pattern | Heavy payloads on list endpoints if applied uniformly; client waste if it only needs IDs |
| **IDs only** | Tiny payloads | Severe N+1 from the *client* side — every brand needs a follow-up call; bad UX |
| **`?include=brand,notes`** opt-in | Caller controls payload weight; well-trodden REST pattern | Schema typing gets harder (every nested field becomes optional); pydantic v2 needs `model_config = ConfigDict(extra="ignore")` and field unions — workable but more code |

**Recommendation: hybrid by endpoint, not by query param.** Let the
*endpoint* dictate the shape rather than introducing `?include=`:
- **List endpoints** (`GET /fragrances`, `GET /brands`, etc.) return
  *summary* schemas (id, slug, name, brand_slug, year_released, gender,
  thumbnail-ish fields). No nested arrays. Pre-load with `selectinload`
  on the parent (brand) only.
- **Detail endpoints** (`GET /fragrances/{slug}`) return *full* schemas
  with brand object, perfumer[] objects, notes grouped by role, articles
  inline. Use `selectinload(Fragrance.brand)`,
  `selectinload(Fragrance.perfumers)`, `selectinload(Fragrance.notes)`,
  optionally `selectinload(Fragrance.articles)`.

This avoids `?include=` complexity while keeping payloads sane. If we
later need to slim or fatten responses, that's a *new* endpoint or a
non-breaking optional flag.

**Articles on fragrance detail**: include them by default (small,
typically 0–3 per fragrance). If volume grows, move behind
`?include=articles` later — non-breaking.

### 3. Filter parameter style

**Recommendation: query string only.** `GET` with body is non-standard,
breaks caching, and tooling (CDN, OpenAPI generators, browser devtools)
treats it poorly. Filters are simple value-equality; query string is
sufficient.

### 4. Slug vs ID in URLs and filters

- **Path segment**: slug only (`/fragrances/aventus`). Confirmed.
- **Filter values**: slug-by-default with explicit `_id` overrides where
  it pays. Concrete recommendation:
  - `?brand=chanel` → slug
  - `?perfumer=jean-claude-ellena` → slug
  - `?accord=floral` → slug
  - `?concentration=edp` → slug
  - `?gender=fem` → already-canonical ENUM value (no slug)
  - `?year_released=2010` → integer
  - `?year_min=2000&year_max=2010` → range
  - **No `?brand_id=<uuid>` form.** UUIDs aren't useful to humans or
    the chatbot's tool-call layer. We can add `_id` later if needed.

### 5. Filter combinatorics (multi-value)

| Style | Example | Semantics |
|---|---|---|
| **Repeated key** | `?accord=floral&accord=woody` | any-of (OR) — FastAPI `list[str]` Query default |
| **CSV** | `?accord=floral,woody` | any-of, but client has to encode |
| **Multiple keys for AND** | `?accord_any=...&accord_all=...` | mixed any/all |

**Recommendation: repeated key with OR semantics.** It is FastAPI-native
(`Annotated[list[str] | None, Query()] = None`), URL-friendly, and
explicit. **No** `accord_all=` in Phase 1 — defer if a real use case
emerges. AND across *different* filters is implicit (`?brand=chanel&gender=fem`
is brand AND gender).

### 6. Default + max page size

**20 default, 100 max.** Validated via `Annotated[int, Query(ge=1, le=100)] = 20`.
Matches FastAPI tutorial idiom and keeps payloads small enough to fit a
typical Vercel response budget without compression headaches.

### 7. Response envelope

| Option | Example |
|---|---|
| **Envelope `{data, pagination}`** | `{"data": [...], "pagination": {"total": 1234, "limit": 20, "offset": 40}}` |
| **Flat array + `Link` header** | RFC-5988-ish |
| **JSON:API** | `{"data": [{type, id, attributes, relationships}, ...]}` |

**Recommendation: simple envelope.** Format:

```json
{
  "data": [...],
  "pagination": {"total": 1234, "limit": 20, "offset": 40}
}
```

Rationale: `Link` headers are awkward in fetch-based JS clients.
JSON:API is heavy for a small public read API. Envelope keeps total in
one place, plays well with `openapi-typescript`-generated types
(envelope is its own pydantic model, list type is generic), and gives
us room to add `links`/`meta` later without breaking.

### 8. Sort options

**Recommendation: fixed sensible defaults per resource; one optional
sort knob in Phase 1.**
- `GET /fragrances` default sort: `year_released DESC NULLS LAST,
  name ASC`. Knob: `?sort=year_released:desc|year_released:asc|name:asc|name:desc`.
  Whitelist; reject anything else.
- `GET /brands` default: `name ASC`.
- `GET /perfumers` default: `name ASC`.
- `GET /articles` default: `published_at DESC NULLS LAST, slug ASC`.

Defer arbitrary multi-key sorts and full free-form sort syntax.

### 9. 404 behavior

**Recommendation: `404 Not Found`** with body
`{"detail": "Fragrance with slug 'foo' not found"}`. No `410 Gone` —
we don't track tombstones. No `200 + null/empty` — that's an antipattern
for type-safe clients.

For list endpoints with filters that match nothing: return
`200 OK` with `{"data": [], "pagination": {"total": 0, ...}}`. Empty
result is not an error.

### 10. Trailing slashes

FastAPI by default 307-redirects `/foo/` to `/foo` (or vice versa
depending on declaration). Recommendation: **declare every route
without a trailing slash and disable redirect** (`FastAPI(redirect_slashes=False)`)
to keep behavior strict and observable, and to avoid 307 → 200 chains
through Fly.io's edge.

### 11. API versioning prefix

**Recommendation: `/api/v1/` from day one.** Costs nothing now; a rename
later means coordinated migration in the web app, the LangGraph tools,
any external embedder, plus search engines. We will never have v0; v1
is correct.

The static Swagger UI stays at `/docs` (FastAPI default). The OpenAPI
schema stays at `/openapi.json`. Versioning applies only to data routes.

### 12. OpenAPI / docs

- **Custom tags per resource.** `Fragrances`, `Brands`, `Perfumers`,
  `Notes`, `Accords`, `Articles`. Use `APIRouter(prefix="/fragrances",
  tags=["Fragrances"])`. Add `openapi_tags=[...]` metadata to `FastAPI()`
  with one-line descriptions.
- **Response examples**: auto from pydantic v2 (`model_config = ConfigDict(
  json_schema_extra={"examples": [{...}]})`) on each schema. Hand-curated
  one example per response model — cheap, high payoff for the docs UI.
- **`/docs` location**: keep at the FastAPI default. No need to move.
- **Static `apps/api/openapi.json`**: yes, emit one. Two reasons:
  1. The web app (Phase 4) will use `openapi-typescript` against a
     committed file so PRs visibly diff API changes.
  2. CI can fail when the committed JSON drifts from the live schema.
  - Recommended: a `just openapi-export` recipe that calls
    `python -c "import json; from fragwise_api.main import app;
    print(json.dumps(app.openapi()))"` and a CI step that diffs.

### 13. Pydantic models — placement and shape

| Option | Pros | Cons |
|---|---|---|
| **Per-route file co-located** (`api/v1/fragrances.py` defines schemas + handlers) | Locality; easy to grep | Cross-resource references (FragranceSummary inside BrandDetail) cause circular imports |
| **Single `schemas.py`** | One place, no circulars | Big file once we add 12 endpoints × ~3 schemas each |
| **Per-resource module** (`api/v1/schemas/fragrance.py`, `brand.py`, ...) with shared `pagination.py`, `_common.py` | Clean imports; matches model layout | Slightly more boilerplate |

**Recommendation: per-resource module under `api/v1/schemas/`.** Mirrors
`db/models/` layout, prevents circular imports because shared
"summary" types (`BrandSummary`, `PerfumerSummary`, `NoteSummary`) live
beside the resource and are imported into `fragrance.py` for the detail
schema. One `pagination.py` for the envelope generic.

Composability: define `FragranceSummary` and `FragranceDetail` (the
detail extends summary by adding nested fields). This keeps list
payloads light without duplicating fields.

### 14. Performance / caching

- **Redis caching**: not needed in Phase 1. Postgres + B-tree indexes
  on slugs + the GIN FTS index handle <50K-row reads fine. Adding
  Upstash Redis means cache invalidation pain, an extra dep, and the
  free tier is precious. **Defer.**
- **HTTP caching**: yes, set `Cache-Control: public, max-age=60,
  stale-while-revalidate=300` on the read endpoints. Cheap; CDN-friendly
  if Fly.io ever sits behind one. ETag is overkill — no client needs
  conditional GETs in Phase 1.
- **N+1 strategy**: `selectinload` for collections (`Fragrance.notes`,
  `Fragrance.perfumers`, `Fragrance.articles`), `joinedload` for the
  required to-one (`Fragrance.brand`, `Fragrance.concentration`).
  Per Context7 SQLAlchemy 2.0 async docs, `selectinload` is the
  asyncio-recommended choice for collections (a second SELECT with
  IN-clause, no implicit lazy I/O). `joinedload` is fine for to-one
  on the same row.

### 15. Rate limiting

**Recommendation: not in Phase 1.** Read-only public traffic is low risk.
Add before public launch (separate change), most likely **slowapi**
(in-process leaky bucket; no infra) or **Upstash rate-limit** if Redis is
already wired up. Per-IP. The chatbot tool-call path will need its own
budget logic later (Phase 3) — orthogonal.

Flag: this is a delayed risk, not a missing requirement. The spec for
Phase 1 should explicitly note "no rate limiting; assume low traffic
and trusted callers."

### 16. Tooling — FastAPI 0.128 patterns to lock in

- `Annotated[T, Query(...)]` for every query param. **No** `Query()` as
  default value. Confirmed by Context7 FastAPI docs ("Annotated is the
  recommended approach in modern FastAPI applications").
- `Annotated[FilterParams, Query()]` (pydantic-model-as-Query) is
  available in 0.128 and worth using once a route has 4+ filters
  (e.g., `GET /fragrances`). Reduces signature noise; gives us pydantic
  validation in one place.
- `response_model=PaginatedFragrances` per route — clean OpenAPI shape.
- `APIRouter(prefix="/fragrances", tags=["Fragrances"])` per resource;
  mounted into the app at `/api/v1`.
- Slug regex validation via `Annotated[str, Path(pattern=r"^[a-z0-9-]+$")]`.

## Recommendation: Splitting

**Do not split.** Keep all 12 endpoints under `phase-1-catalog-read-endpoints`.

Reasons:
- Conventions (pagination envelope, sort syntax, filter style, error
  shape, schema layout) MUST be set once. Splitting risks `1a` and `1b`
  diverging on those decisions.
- The endpoints are mechanically uniform — list + detail × 6 resources.
  Once one resource is implemented, the rest are copy-shape work.
- Test infrastructure (testcontainers fixture, seed fixtures) gets
  written once in tasks 1.x and reused.
- Total surface is bounded: 12 routes, ~6 routers, ~12–15 pydantic
  schemas. That's well within a single change envelope.

What WOULD justify splitting later: if the accord-linkage gap (see
"Hard Gaps" below) blocks `GET /accords/{slug}/fragrances` and we need
to ship 11 endpoints now and the accord-detail one in `phase-1b`. That's
a contingent split, not a planned one.

## Hard Gaps (must resolve in `proposal.md` or `design.md`)

1. **Accord ↔ fragrance link is missing in the schema.** No
   `fragrance_accords` table, no derivation rule. Three options:
   - **(a) Add a `fragrance_accords` M:M join** (mirrors `fragrance_notes`
     minus the role enum). Author-supplied via seed YAML. Schema delta
     belongs in this phase or in a tiny `phase-1-prelude`.
   - **(b) Derive accords from notes** via an ontology mapping
     (`packages/ontology/note_to_accord.yaml`). Ships with no schema
     change but adds a runtime computation per fragrance (cacheable,
     small). Risk: duplicates editorial intent.
   - **(c) Drop `GET /accords/{slug}` paginated fragrances list from
     Phase 1.** Keep `GET /accords` (flat list, cacheable). Punt the
     filter-by-accord and accord-detail-fragrances to a later change.
   - **Recommended: (a)**. It's a 1-table delta. Author-supplied is
     more defensible than algorithmic derivation. Folds neatly into the
     existing seed YAML format. Spec it as part of Phase 1's
     `data-model` delta and add the join model in `db/models/joins.py`.

2. **ORM `relationship()` declarations not yet defined for the M:M
   sides.** `Fragrance` has no `notes`, `perfumers`, or `articles`
   relationship attribute. `Note` has no `parent`/`children` self-ref
   (needed for the `GET /notes` tree response). These are required for
   `selectinload` to work cleanly. Phase 1 must add them.
   - This is a *non-breaking schema-side ORM change*; no new tables, no
     migration. It belongs in this phase's design, not a separate one.

3. **Note tree shape**. `GET /notes` is described as "tree-shaped".
   Cheapest implementation: load all notes in one query, build the
   tree in Python, return `[{slug, name, children: [...]}]`. With
   ~100–500 notes total, this is fine and cacheable. Decision: pick
   this in `design.md` and don't go down the recursive-CTE path
   prematurely.

## Risks

- **Contract lock-in**: The shape we ship freezes the web client and
  any external consumer (the OSS hostable API). Mitigation: thorough
  pydantic schema review and one round of `judgment-day` on the design
  before code lands.
- **N+1 in detail endpoints**: easy to introduce by forgetting a
  `selectinload`. Mitigation: integration test that asserts the query
  count for `GET /fragrances/{slug}` is ≤ N (target N=4: fragrance +
  notes + perfumers + articles, with brand joinloaded inline).
- **Bad pagination at depth**: not a real risk at <50K rows, but if the
  catalog 10x's later, offset perf degrades. Mitigation: keep the
  envelope shape extensible (cursor can be added as a sibling field).
- **Filter combinatorics**: multi-accord OR plus brand AND plus year
  range is fine in SQL; the risk is the UI building bad queries.
  Mitigation: cap filter values (e.g., max 10 accord values per request)
  via `Query(max_length=10)` on the list type.
- **Schema drift between live `app.openapi()` and committed
  `openapi.json`**: web build will silently keep old types. Mitigation:
  CI step diffing the two.
- **Accord gap (see Hard Gap #1)**: if not resolved, two endpoints in
  the brief don't fit. Mitigation: pick option (a) above in `proposal.md`.
- **`/healthz` and `/readyz` currently live at root**: they will not be
  prefixed under `/api/v1/`. That's correct — health probes are
  infra-level — but spec it explicitly so future routers don't migrate
  them by accident.

## Trade-offs to flag (for the proposal)

- **Nested vs `?include=`**: chose nested-by-endpoint (lists slim,
  details fat). Loses caller flexibility; gains type clarity.
- **Offset vs cursor**: chose offset for simplicity. Loses scaling
  headroom; gains debuggability and standard tooling.
- **`/api/v1/` now**: chose to prefix from day one. Tiny upfront cost;
  saves a coordinated migration later.
- **No Redis caching**: chose Postgres-only. Loses microsecond cache
  hits; gains operational simplicity and zero free-tier usage.
- **No rate limiting**: chose to defer. Loses public-launch readiness;
  gains scope clarity (Phase 1 is API surface, not posture). Tracked
  for a follow-up change before any marketing push.
- **Author-supplied accords (option (a) in Hard Gap #1)**: chose to
  expand the schema. Loses "pure" derivation purity; gains editorial
  control and testability.

## Ready for Proposal

**Yes**, with three decisions to surface in the proposal:
1. Lock in offset+limit, nested-by-endpoint, `/api/v1/` prefix, simple
   envelope, slug-based filters with repeated-key OR.
2. Resolve the accord ↔ fragrance gap (recommended: add
   `fragrance_accords` M:M join via a `data-model` spec delta in this
   change).
3. Confirm the change is NOT split — all 12 endpoints land together.

The orchestrator should hand `sdd-propose` a brief that includes those
three decisions plus the Phase-1 scope statement (read-only, public,
no auth, no chatbot).
