# Proposal: Phase 1 — Catalog Read Endpoints

## Intent

Ship the read-only public catalog API: 12 endpoints (list + detail for fragrances, brands, perfumers, notes, accords, articles) under `/api/v1/`. Unblocks the Phase 4 web client and the Phase 3 chatbot tool-call layer. Locks API conventions (envelope, pagination, filters, errors) once.

## Scope

### In Scope
- `fragrance_accords` M:M join table + Alembic revision `0002` (B-tree indexes on FKs, unique pair).
- ORM `relationship()` additions on `Fragrance` (`notes`, `perfumers`, `articles`, `accords`) and `Note` (`parent`, `children`). Non-breaking.
- 6 routers under `apps/api/src/fragwise_api/api/v1/` (`fragrances`, `brands`, `perfumers`, `notes`, `accords`, `articles`); 12 endpoints; `/api/v1/` prefix; `redirect_slashes=False`.
- Pydantic v2 response schemas under `api/v1/schemas/` (per-resource module, slim list / fat detail).
- Filter module for `/fragrances`: brand, perfumer, gender, year_min/year_max, concentration, accord (multi-value OR), note (multi-value OR).
- Static `apps/api/openapi.json` emit script + `just emit-openapi` recipe + CI drift gate.
- Integration tests: per-endpoint happy path, pagination edge, 404, multi-value OR filters, query-count assertion (≤4 SELECTs on detail).

### Out of Scope
- Rate limiting (separate change before public launch — carry-forward).
- Redis caching, ETag/Cache-Control, search/recsys, chatbot, write endpoints, auth.

## Capabilities

### New Capabilities
- None. (`api-app` already exists; we extend it. `sdd-spec` MAY split off a `catalog-api` capability if the requirement bundle warrants it — flag for spec phase.)

### Modified Capabilities
- `api-app`: add 12 catalog route requirements, envelope shape, pagination, filter contract, OpenAPI emission.
- `data-model`: add `fragrance_accords` join table; add ORM relationship requirements.
- `repo-skeleton`: widen permitted paths to include `apps/api/src/fragwise_api/api/**` and `apps/api/scripts/**`.

## Approach

Per-resource `APIRouter(prefix=..., tags=[...])` mounted at `/api/v1`. `Annotated[T, Query(...)]` everywhere. `selectinload` for collections, `joinedload` for to-one. Slim list schemas; fat detail schemas with nested brand/perfumers/notes-by-role/articles. Envelope `{data, pagination}` for lists; bare object for detail; `{error}` for errors. Slug-based paths and filter values; repeated-key OR semantics for multi-value. 404 on missing slug; 200 + empty `data: []` on no-match. Static `openapi.json` committed; CI verifies it matches `app.openapi()`.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `apps/api/src/fragwise_api/api/v1/` | New | 6 routers + schemas dir |
| `apps/api/src/fragwise_api/db/models/` | Modified | ORM relationships; new `FragranceAccord` |
| `apps/api/alembic/versions/0002_*.py` | New | `fragrance_accords` table |
| `apps/api/scripts/emit_openapi.py` | New | OpenAPI emit script |
| `apps/api/openapi.json` | New | Committed artifact |
| `apps/api/tests/integration/` | Modified | Per-router test files |
| `apps/api/src/fragwise_api/main.py` | Modified | Mount routers, openapi tags |
| `justfile` | Modified | `emit-openapi` recipe |
| `.github/workflows/api.yml` | Modified | OpenAPI drift CI step |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Endpoint shape locks web client | High | `judgment-day` on design before apply |
| N+1 regressions | Med | Query-count integration test |
| `openapi.json` drift | Med | CI gate diffing committed vs runtime |
| Multi-value SQL complexity | Low | Spec scenarios cover OR + AND combos |
| Seed misses accord rows | Med | Sub-task: extend seed YAML format for accords |
| No rate limit at public launch | High (later) | Tracked as carry-forward change |

## Rollback Plan

- Pre-merge: `git reset`.
- Post-merge, pre-deploy: revert merge commit.
- Post-deploy: `alembic downgrade -1` drops `fragrance_accords`. All routes are read-only — no data corruption risk; only join rows lost.

## Dependencies

- Phase 0a/0b/0c complete (FastAPI scaffold, ORM models, Alembic baseline) — done.

## Success Criteria

- [ ] All 12 endpoints respond per spec; 404 on missing slug; 200+empty on no-match.
- [ ] `selectinload`/`joinedload` enforced; query-count test passes (≤4 on fragrance detail).
- [ ] `apps/api/openapi.json` committed; CI fails on drift.
- [ ] Integration tests pass; ruff + mypy strict clean.
- [ ] `judgment-day` review of design completes before `sdd-apply`.
