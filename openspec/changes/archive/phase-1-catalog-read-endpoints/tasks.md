# Tasks: Phase 1 — Catalog Read Endpoints

> Implementation order is dependency-strict. **Task 2.1 (F1 schema layout) MUST run before any router or schema-importing test.** Apply-time follow-ups F1-F9 from `design.md §"Known Follow-ups for Apply Phase"` are NOT separate tasks — they are verification sub-checks within the relevant tasks (annotated inline below).

## Phase 1: Pre-flight

- [x] 1.1 Confirm clean branch state and P0c artifacts present: ORM models in `apps/api/src/fragwise_api/db/models/`, Alembic baseline `0001_*.py`, `data/seed/minimal_fragrances.yaml` exists. `git status` clean. (~5 min)

## Phase 2: Schema Layout Refactor (F1 — BLOCKING)

- [x] 2.1 **(F1)** Create `apps/api/src/fragwise_api/api/v1/schemas/summaries.py`; move all `*Summary` classes from per-resource modules into it; refactor imports in `fragrance.py` and detail modules (`brand.py`, `perfumer.py`, `note.py`, `accord.py`, `article.py`) to import summaries from `summaries.py`. Verify: `uv run python -c "from fragwise_api.api.v1 import schemas"` exits 0. **Must complete before Phase 5/6.** (~20 min)

## Phase 3: Data-Model Delta

- [x] 3.1 Add `FragranceAccord` ORM class in `apps/api/src/fragwise_api/db/models/fragrance.py` per `design.md §"FragranceAccord"`: B-tree indexes on FKs, `UniqueConstraint(fragrance_id, accord_id)`. (~15 min)
- [x] 3.2 Add `relationship()` declarations on `Fragrance` (`notes`, `perfumers`, `articles`, `accords`), `Note` (`parent`, `children`), `Brand`, `Perfumer`, `Accord`, `Article`, `FragranceNote` per `design.md §"ORM relationships"`. Use `back_populates` everywhere. (~20 min)
- [x] 3.3 Create Alembic revision `apps/api/alembic/versions/0002_fragrance_accords.py`; `op.create_table('fragrance_accords', ...)` with FK indexes + unique pair; downgrade drops table. Verify `alembic upgrade head` and `alembic downgrade -1` round-trip. (~20 min)

## Phase 4: Common API Layer

- [x] 4.1 Create `apps/api/src/fragwise_api/api/__init__.py` and `apps/api/src/fragwise_api/api/v1/__init__.py` (router aggregation: `api_v1_router = APIRouter(prefix="/api/v1")` then `include_router` for each of 6 resource routers). (~10 min)
- [x] 4.2 Create `api/v1/deps.py` per `design.md §"deps.py"`: `DbSessionDep`, `PaginationDep`. (~10 min)
- [x] 4.3 Create `api/v1/pagination.py` per `design.md §"pagination.py"`. **R3 fix**: `paginate()` counts rows of the filtered subquery directly (no `pk_column` parameter). Apply verbatim. (~15 min)
- [x] 4.4 Create `api/v1/errors.py` (custom `NotFoundError`, exception handlers returning `{"error": {...}}` envelope) and `api/v1/sorts.py` (sort-key parsing + whitelist). (~15 min)
- [x] 4.5 Create `api/v1/filters.py` per `design.md §"filters.py"`: `FragranceListQuery`, `BrandListQuery`, `PerfumerListQuery`, `NoteListQuery`, `AccordListQuery`, `ArticleListQuery` with `Annotated[T, Query(...)]`. (~25 min)

## Phase 5: Schemas

- [x] 5.1 Create `api/v1/schemas/common.py` per `design.md §"common.py"` (envelope, `PaginationMeta`, `ErrorEnvelope`). (~10 min)
- [x] 5.2 Create `api/v1/schemas/fragrance.py` (`FragranceListItem`, `FragranceDetail` with nested brand/perfumers/notes-by-role/accords/articles). Imports `*Summary` from `summaries.py`. (~20 min)
- [x] 5.3 Create per-resource detail modules: `brand.py`, `perfumer.py`, `concentration.py`, `note.py` (depth-2 children tree), `accord.py`, `article.py`. All `*Summary` imports come from `summaries.py`. (~25 min)
- [x] 5.4 Create `api/v1/schemas/__init__.py` with centralized `model_rebuild()` loop per `design.md §"schemas __init__"`. **Verify F1**: `uv run python -c "from fragwise_api.api.v1 import schemas"` exits 0 with no `PydanticUndefinedAnnotation`. (~10 min)

## Phase 6: Routers

- [x] 6.1 Create `api/v1/routers/fragrances.py` (list + detail) per `design.md §"fragrances.py"`. `_apply_filters` uses local variables (no Pydantic mutation). `selectinload` on collections, `joinedload` on to-one. (~30 min)
- [x] 6.2 Create `api/v1/routers/brands.py` and `perfumers.py`. Use `BrandListQueryDep` (NOT `Depends()`). Apply **R2-W2 ILIKE escape** pattern (escape `\`, `%`, `_` then `escape="\\"`). (~25 min)
- [x] 6.3 Create `api/v1/routers/notes.py` (list + tree depth-2), `accords.py`, `articles.py` per design. (~25 min)

## Phase 7: Main App Wiring

- [x] 7.1 Update `apps/api/src/fragwise_api/main.py`: `redirect_slashes=False`, mount `api_v1_router`, register exception handlers from `errors.py`, add CORS middleware per `design.md §"main.py"` (**R2-W1 fallback**: explicit `allow_origins` list, `allow_credentials=False`). (~15 min)

## Phase 8: OpenAPI Emission

- [x] 8.1 Create `apps/api/scripts/emit_openapi.py` per `design.md §"emit_openapi.py"`: imports app, writes `app.openapi()` JSON to `apps/api/openapi.json`. Add `just emit-openapi` recipe in root `justfile`. (~15 min)
- [x] 8.2 Add CI step in `.github/workflows/api.yml` after `just emit-openapi`: `git diff --exit-code apps/api/openapi.json`. Commit initial `openapi.json`. (~10 min)

## Phase 9: Seed Extension (S4 + R2-W5)

- [x] 9.1 Extend `data/seed/minimal_fragrances.yaml`: add `accords:` field per fragrance + a depth-2 note hierarchy entry. (~10 min)
- [x] 9.2 Update `data/scripts/seed_minimal_fragrances.py` to upsert `fragrance_accords` rows. **Verify F1**: seed runs end-to-end after schema refactor. (~15 min)

## Phase 10: Integration Tests

- [x] 10.1 `tests/integration/test_fragrances.py`: list + detail happy paths; pagination edges; multi-value OR (accord, note); 404 on missing slug; **query-count fixture asserts ≤6 SELECTs on detail, ≤4 baseline**. (~30 min)
- [x] 10.2 `tests/integration/test_brands.py` + `test_perfumers.py`: list/detail, search filter, **F5 ILIKE-escape edge tests** (`%`, `_`, `\` in query). (~25 min)
- [x] 10.3 `tests/integration/test_notes.py`: tree endpoint asserts depth-2 nesting; `test_accords.py` + `test_articles.py` happy paths. (~20 min)
- [x] 10.4 `tests/integration/test_envelope.py`: list envelope shape, error envelope shape, `redirect_slashes=False` (trailing slash → 404, not 307), CORS headers (**F6 trip**: `allow_credentials=False` with `allow_origins=["*"]` does NOT echo origin as wildcard with credentials). (~20 min)
- [x] 10.5 `tests/integration/test_openapi_drift.py`: load committed `openapi.json`, compare to `app.openapi()`, fail on diff. **Verify F3**: `configure_mappers()` emits no SAWarning during test collection. (~15 min)

## Phase 11: Self-Check

- [x] 11.1 `uv sync` clean; `just lint-api` (ruff + mypy strict) green; `just test-integration` green. (~10 min)
- [x] 11.2 Run apply-time follow-ups verification F1-F9 per `design.md §"Known Follow-ups for Apply Phase"`: F1 schema import 0-exit (verified — `from fragwise_api.api.v1 import schemas` exits 0), F2 envelope shape (additive ORM diffs only; `position` and indexes preserved on `FragranceNote`; `parent_id` `ondelete="RESTRICT"` and indexes preserved on `Note`), F3 no SAWarning (`Base.registry.configure()` clean under `warnings.simplefilter('error')`; integration test enforces), F4 query-count fixture (test_fragrances::test_detail_query_count_bounded asserts ≤6 SELECTs), F5 ILIKE escape (`?q=%`, `?q=_`, `?q=foo\bar`, `?q=50%` all return zero rows), F6 CORS credentials (`Access-Control-Allow-Credentials` is absent or `false`), F7 `redirect_slashes` (`/api/v1/fragrances/` returns 404 with no Location header), F8 OpenAPI drift (`test_openapi_drift` byte-equality passes), F9 seed accords (extended seed YAML+script load successfully). (~20 min)
- [x] 11.3 Verify permitted-paths boundary: `git ls-files | grep '\.py$' | grep -vE '<permitted_paths_pattern>'` returns empty. Cross-check against `repo-skeleton` delta spec. New paths added: `apps/api/src/fragwise_api/api/**`, `apps/api/scripts/**`, `apps/api/tests/integration/api/v1/**` — all within `apps/api/**` permission. (~5 min)

---

**Total: 28 tasks across 11 phases.** Within the ≤30 budget. No tasks deferred or merged.
