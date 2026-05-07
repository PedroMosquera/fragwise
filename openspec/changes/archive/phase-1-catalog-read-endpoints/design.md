# Design: Phase 1 — Catalog Read Endpoints

> **Process Gate**: This design MUST be reviewed via `judgment-day` (parallel
> adversarial review) BEFORE `sdd-tasks` and `sdd-apply` run. The proposal
> flagged "Endpoint shape locks web client" as the highest risk; the dual-judge
> pass is the mitigation. Do NOT proceed to implementation until both judges
> pass on the same iteration of this file.

## Technical Approach

A read-only public catalog HTTP surface composed of 6 per-resource
`APIRouter` instances (`fragrances`, `brands`, `perfumers`, `notes`,
`accords`, `articles`), each producing list + detail handlers, mounted under
`/api/v1/`. Pydantic v2 schemas split per resource into "list-shape" (slim)
and "detail-shape" (fat). Eager loading is mandatory: `joinedload` for to-one,
`selectinload` for collections, `lazy="raise_on_sql"` on every relationship
to make N+1 a dev-time crash. Pagination uses offset+limit with a separate
`SELECT count(*)` for `total`. Errors flow through one envelope:
`{"error": {"code, "message", "detail"}}`. The OpenAPI document is committed
to `apps/api/openapi.json` and CI fails on drift.

Reference: `specs/catalog-api/spec.md`, `specs/data-model/spec.md`,
`specs/api-app/spec.md`, `specs/repo-skeleton/spec.md`.

## Architecture Decisions (ADRs)

| ID | Decision | Choice | Why |
|----|----------|--------|-----|
| 0019 | Notes-by-role access | **Association object `FragranceNote` + association_proxy `notes` for plain list** + Python-side mapper that groups into `{top, heart, base}` for response | We already have the `FragranceNote` association class with the `role` enum (in `db/models/joins.py`). Keep it, surface a plain `notes: list[Note]` proxy for filter joins, and group-by-role in the response mapper. Simpler than reshaping ORM around a dict-keyed collection |
| 0020 | Lazy-load discipline | **`lazy="raise_on_sql"` on every relationship** | Makes N+1 a crash at dev time, not a perf bug in prod. Pairs with the query-count integration test |
| 0021 | Default list sort | **`name ASC` (or `title ASC` for articles) + `id ASC` tiebreaker** for every list endpoint in Phase 1; sort knob deferred | Spec invariant. The `id ASC` tiebreaker (UUID v7 PKs are time-sortable) prevents row-shift between pages when same-name rows fall on a page boundary. `year_released DESC NULLS LAST` is desirable for catalog UI; left as a per-router constant `DEFAULT_SORT` so the catalog UI change can flip one line later. Articles use `Article.title` (no `name` column) |
| 0022 | OpenAPI emission | **Static `apps/api/openapi.json` + byte-equality CI gate; `FastAPI(version="0.1.0")` pinned, decoupled from `pyproject.version`; FastAPI/Pydantic patch versions pinned** | Web app types regenerate from a committed file. Pinning the OpenAPI `info.version` to `"0.1.0"` (not `pyproject.version="0.0.0"`) prevents CI churn on package version bumps. Additionally: pin **exact** patch versions of `fastapi==0.128.X` and `pydantic==2.X.Y` in `pyproject.toml` `[project] dependencies` (not `>=`); any `uv lock --upgrade` of those packages requires re-running `just emit-openapi` and committing the diff. CI failure prints `Run 'just emit-openapi' and commit the diff.` |
| 0023 | Pagination total | **Separate `SELECT count(*)`** over `func.count().over()` window | Two clear queries beat one window-aggregating query. CPU per row matters more at scale; split is easier to read and easier to cache later. **Trade-off accepted (eventual consistency)**: the count and the row query run as two separate statements; concurrent inserts/deletes between them can cause a ±1 row skew between `total` and the visible `data` length. This is acceptable for a public read API and matches what most paginated APIs ship. If strict consistency is later required, wrap `paginate()` in `async with session.begin(): await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))` (Postgres) or use a single windowed query. The implementation deliberately does NOT do this in Phase 1 |
| 0024 | CORS configuration | **Lookup precedence `CORS_ALLOW_ORIGIN` then `NEXT_PUBLIC_API_URL` then `*`**; comma-separated list parsed into multiple origins; documented in `.env.example` | The catalog-api spec scenario sets `NEXT_PUBLIC_API_URL=https://fragwise.app` and asserts that origin is allowed; design must honor it. We honor `CORS_ALLOW_ORIGIN` first (server-side primary), fall back to `NEXT_PUBLIC_API_URL` (matches the spec scenario), then default to `*` in dev. Comma-separated values (e.g. `https://fragwise.app,https://staging.fragwise.app`) are split on `,`, stripped, and passed as a list to `allow_origins` |
| 0025 | Capability split | **New `catalog-api` capability spec**, separate from `api-app` | The 12 catalog-route requirements deserve their own spec. `api-app` keeps the cross-cutting concerns (mount path, OpenAPI emission, health probes) |

## Directory Layout

```
apps/api/src/fragwise_api/
  api/
    __init__.py
    v1/
      __init__.py            # router aggregation
      deps.py                # FastAPI deps (db session, common Query)
      pagination.py          # LimitOffsetParams, paginate()
      errors.py              # ApiError, errors_envelope, exception handlers
      sorts.py               # DEFAULT_SORT constants per router
      filters.py             # Pydantic filter models (FragranceFilters, etc.)
      schemas/
        __init__.py          # centralized model_rebuild() of all forward refs
        common.py            # Pagination, ListEnvelope[T], ErrorBody
        brand.py             # BrandSummary, BrandDetail
        perfumer.py          # PerfumerSummary, PerfumerDetail
        concentration.py     # ConcentrationSummary
        note.py              # NoteSummary, NoteDetail, NoteTreeNode
        accord.py            # AccordSummary, AccordDetail
        article.py           # ArticleSummary, ArticleDetail
        fragrance.py         # FragranceListItem, FragranceDetail, NotesByRole
      routers/
        __init__.py
        fragrances.py
        brands.py
        perfumers.py
        notes.py
        accords.py
        articles.py
  scripts/
    __init__.py
    emit_openapi.py
```

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `apps/api/src/fragwise_api/main.py` | Modify | `redirect_slashes=False`; mount `api_router`; install CORS; install error handlers; `version="0.1.0"`; `readyz` masks DB error |
| `apps/api/src/fragwise_api/api/__init__.py` | Create | Empty marker |
| `apps/api/src/fragwise_api/api/v1/__init__.py` | Create | Aggregates 6 routers under `/api/v1` |
| `apps/api/src/fragwise_api/api/v1/deps.py` | Create | DB session dep, common query deps |
| `apps/api/src/fragwise_api/api/v1/pagination.py` | Create | `LimitOffsetParams`, `paginate()` |
| `apps/api/src/fragwise_api/api/v1/errors.py` | Create | `ApiError`, exception handlers, error envelope helper |
| `apps/api/src/fragwise_api/api/v1/sorts.py` | Create | `DEFAULT_SORT` per router |
| `apps/api/src/fragwise_api/api/v1/filters.py` | Create | `FragranceFilters`, `BrandFilters`, `PerfumerFilters` (Pydantic Query models) |
| `apps/api/src/fragwise_api/api/v1/schemas/__init__.py` | Create | Centralized `model_rebuild()` orchestration with explicit namespace |
| `apps/api/src/fragwise_api/api/v1/schemas/*.py` | Create | 8 schema modules |
| `apps/api/src/fragwise_api/api/v1/routers/*.py` | Create | 6 router modules |
| `apps/api/src/fragwise_api/db/models/joins.py` | Modify | Add `FragranceAccord` class |
| `apps/api/src/fragwise_api/db/models/fragrance.py` | Modify | Add 4 collection relationships + `notes` association_proxy |
| `apps/api/src/fragwise_api/db/models/brand.py` | Modify | `lazy="raise_on_sql"` on `fragrances` |
| `apps/api/src/fragwise_api/db/models/perfumer.py` | Modify | Add `fragrances` relationship |
| `apps/api/src/fragwise_api/db/models/accord.py` | Modify | Add `fragrances` relationship |
| `apps/api/src/fragwise_api/db/models/note.py` | Modify | Add `parent`, `children`, `fragrances` relationships |
| `apps/api/src/fragwise_api/db/models/article.py` | Modify | Add `fragrances` relationship |
| `apps/api/src/fragwise_api/db/models/__init__.py` | Modify | Re-export `FragranceAccord` |
| `apps/api/alembic/versions/0002_fragrance_accords.py` | Create | New migration |
| `apps/api/scripts/__init__.py` | Create | Empty marker |
| `apps/api/scripts/emit_openapi.py` | Create | OpenAPI emit script |
| `apps/api/openapi.json` | Create | Committed snapshot |
| `apps/api/pyproject.toml` | Modify | Pin exact `fastapi==0.128.X` and `pydantic==2.X.Y` patch versions |
| `apps/api/.env.example` | Modify | Add `CORS_ALLOW_ORIGIN=*` and document `NEXT_PUBLIC_API_URL` fallback + comma-list syntax |
| `apps/api/tests/conftest.py` | Modify | Re-export integration fixtures via `pytest_plugins` |
| `apps/api/tests/integration/api/v1/conftest.py` | Create | Seed fixtures, query-count counter |
| `apps/api/tests/integration/api/v1/test_*.py` | Create | 8 integration test modules |
| `data/seed/minimal_fragrances.yaml` | Modify | Extend schema with `accords:` array per fragrance |
| `data/scripts/seed_minimal_fragrances.py` | Modify | Upsert `fragrance_accords` rows from new YAML field |
| `justfile` | Modify | Add `emit-openapi` recipe |
| `.github/workflows/api.yml` | Modify | Add OpenAPI emit + drift gate step (failure prints `just emit-openapi` hint) |

## Data Flow

```
client ──HTTP──> FastAPI app
                    │
                    │ 1. CORSMiddleware (preflight)
                    │ 2. exception_handlers (RequestValidationError → 422 envelope,
                    │    HTTPException → envelope, Exception → 500 envelope)
                    │ 3. mount /api/v1 (api_router)
                    │
                    ▼
              APIRouter("fragrances")  ← typed deps: FragranceListQuery
                    │                                 (combined filters+pagination),
                    │                                 AsyncSession
                    │
              build select(...) with selectinload + joinedload
                    │
                    ▼
              SELECT count(*) ──┐
                                │ 2 round-trips for list
              SELECT rows ──────┘
                    │
                    ▼
              Pydantic mapper (FragranceListItem.model_validate)
                    │
                    ▼
              ListEnvelope[FragranceListItem] → JSON
```

## Critical Code Templates (paste-ready)

### `apps/api/src/fragwise_api/api/v1/__init__.py`

```python
"""Catalog API v1 — aggregates per-resource routers under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from .routers import accords, articles, brands, fragrances, notes, perfumers

# Importing schemas package triggers centralized model_rebuild() (see schemas/__init__.py)
from . import schemas as _schemas  # noqa: F401

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(fragrances.router)
api_router.include_router(brands.router)
api_router.include_router(perfumers.router)
api_router.include_router(notes.router)
api_router.include_router(accords.router)
api_router.include_router(articles.router)

__all__ = ["api_router"]
```

### `apps/api/src/fragwise_api/api/v1/deps.py`

```python
"""Shared FastAPI dependencies for /api/v1.

`get_session` reads `app.state.db_sessionmaker`, which is the single source of
truth for the engine (constructed in `lifespan`). No module-level engine.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fragwise_api.db.session import get_session

DbSession = Annotated[AsyncSession, Depends(get_session)]
```

### `apps/api/src/fragwise_api/api/v1/pagination.py`

```python
"""Offset+limit pagination params + helper."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

T = TypeVar("T")


class LimitOffsetParams(BaseModel):
    """Pagination query params; injected as part of a combined query model."""

    model_config = {"extra": "forbid"}

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


# NOTE: do NOT use `Annotated[LimitOffsetParams, Query()]` standalone alongside
# another `Annotated[XxxFilters, Query()]` on the same endpoint. FastAPI
# validates each model independently with `extra="forbid"`, so a key valid for
# one (e.g. `?brand=`) becomes "extra" to the other and yields a false 422.
# Compose a single per-endpoint query model that inherits both — see filters.py.


async def paginate(
    session: AsyncSession,
    stmt: Select,
    *,
    limit: int,
    offset: int,
) -> tuple[list[Any], int]:
    """Run a count(*) query then a windowed row query. Two round-trips total.

    Rationale (ADR-0023): a separate count is clearer than func.count().over()
    and avoids per-row aggregation cost.

    R3 fix: `count_stmt = select(func.count()).select_from(stmt.subquery())`
    counts rows of the filtered subquery. The earlier "double subquery" with
    `select(pk_column).select_from(stmt.subquery())` introduced `pk_column`'s
    table as an implicit FROM, producing a Cartesian product. The simple
    pattern is correct: `stmt.subquery()` materializes the FROM (with any
    JOINs), and `count(*)` counts its rows. Joinedload to-one relationships
    do not inflate the count (LEFT OUTER JOIN, one row per parent), which
    matches our usage (Brand, Concentration). Joinedload to-many would
    inflate; we never use it for collections (selectinload only).

    Race condition: the count and the row query are two separate statements;
    a concurrent insert/delete can cause `total` and `len(data)` to disagree
    by ±1. ADR-0023 documents this as accepted; do not "fix" it without a
    spec change.
    """
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    rows_stmt = stmt.limit(limit).offset(offset)
    rows = list((await session.execute(rows_stmt)).scalars().unique().all())
    return rows, int(total)
```

### `apps/api/src/fragwise_api/api/v1/errors.py`

```python
"""Error envelope + FastAPI exception handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Closed taxonomy of error codes used in the envelope.
# Mapped from HTTP status by `_http_exception_handler`.
ERROR_CODES = {
    "not_found",            # 404 — slug or resource missing
    "method_not_allowed",   # 405 — HTTP method not supported on route
    "conflict",             # 409 — state conflict
    "invalid_params",       # 422 — Pydantic / Query validation failure
    "http_error",           # any other 4xx
    "internal_error",       # 500 — unhandled exception
}


class ApiError(HTTPException):
    """Application-typed HTTP error; maps to the error envelope."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        detail: Any = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.envelope_detail = detail


def errors_envelope(code: str, message: str, detail: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "detail": detail}}


async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=errors_envelope(exc.code, exc.message, exc.envelope_detail),
    )


def _code_for_status(status: int) -> str:
    """Map HTTP status to closed-taxonomy error code (W1)."""
    if status == 404:
        return "not_found"
    if status == 405:
        return "method_not_allowed"
    if status == 409:
        return "conflict"
    if status == 422:
        return "invalid_params"
    if 500 <= status:
        return "internal_error"
    if 400 <= status < 500:
        return "http_error"
    return "http_error"


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=errors_envelope(_code_for_status(exc.status_code), str(exc.detail), None),
    )


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError,
) -> JSONResponse:
    # W7: filter Pydantic error dicts to drop `input` and `ctx` (these reflect
    # user-supplied data and are a reflected-input surface). Keep only the
    # safe trio: `loc`, `msg`, `type`.
    cleaned_errors = [
        {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=errors_envelope("invalid_params", "Invalid request parameters", cleaned_errors),
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=errors_envelope("internal_error", "Internal server error", None),
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)


def not_found(resource: str, slug: str) -> ApiError:
    return ApiError(
        status_code=404,
        code="not_found",
        message=f"{resource} with slug '{slug}' not found",
        detail={"slug": slug},
    )
```

### `apps/api/src/fragwise_api/api/v1/sorts.py`

```python
"""Default sort constants per resource router.

NOTE: Phase 1 locks `name ASC` (or `title ASC` for articles, since Article has
no `name` column) on every list endpoint, plus a stable `id ASC` tiebreaker
on the UUID v7 PK to prevent row-shift between pages when same-name rows fall
on a page boundary (ADR-0021). Catalog UI may want `year_released DESC NULLS
LAST` later; flip the constant here per router when the UI change lands.
"""

from __future__ import annotations

DEFAULT_FRAGRANCE_SORT = "name_asc"   # then id ASC tiebreaker
DEFAULT_BRAND_SORT = "name_asc"
DEFAULT_PERFUMER_SORT = "name_asc"
DEFAULT_ACCORD_SORT = "name_asc"
DEFAULT_ARTICLE_SORT = "title_asc"    # Article has no `name` column
```

### `apps/api/src/fragwise_api/api/v1/filters.py`

```python
"""Filter Pydantic models for list endpoints.

Each list endpoint that supports both filters and pagination uses a single
**combined** query model (multi-inheritance from filters + LimitOffsetParams).
This is the W6 fix: FastAPI validates per-model with `extra="forbid"`, so two
separate `Annotated[..., Query()]` deps on the same endpoint produce false 422s.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field

from fragwise_api.db.enums import Gender

from .pagination import LimitOffsetParams


class FragranceFilters(BaseModel):
    model_config = {"extra": "forbid"}

    brand: str | None = Field(default=None)               # slug
    perfumer: list[str] | None = Field(default=None)      # slugs (OR)
    gender: Gender | None = Field(default=None)
    year_min: int | None = Field(default=None, ge=1700, le=2100)
    year_max: int | None = Field(default=None, ge=1700, le=2100)
    concentration: str | None = Field(default=None)       # slug
    accord: list[str] | None = Field(default=None, max_length=10)  # slugs (OR)
    note: list[str] | None = Field(default=None, max_length=20)    # slugs (OR)


class FragranceListQuery(FragranceFilters, LimitOffsetParams):
    """Combined filters + pagination for `GET /fragrances`."""

    model_config = {"extra": "forbid"}


class BrandFilters(BaseModel):
    model_config = {"extra": "forbid"}

    q: str | None = Field(default=None, max_length=100)   # case-insensitive substring on `name`


class BrandListQuery(BrandFilters, LimitOffsetParams):
    model_config = {"extra": "forbid"}


class PerfumerFilters(BaseModel):
    model_config = {"extra": "forbid"}

    q: str | None = Field(default=None, max_length=100)   # case-insensitive substring on `name`


class PerfumerListQuery(PerfumerFilters, LimitOffsetParams):
    model_config = {"extra": "forbid"}


# Detail endpoints with a paginated nested `fragrances` array reuse plain
# LimitOffsetParams (no filters) — see routers.
FragranceListQueryDep = Annotated[FragranceListQuery, Query()]
BrandListQueryDep = Annotated[BrandListQuery, Query()]
PerfumerListQueryDep = Annotated[PerfumerListQuery, Query()]
```

### `apps/api/src/fragwise_api/api/v1/schemas/common.py`

```python
"""Cross-resource pydantic schemas: pagination, list envelope, error body."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Pagination(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    limit: int
    offset: int
    total: int
    has_next: bool


class ListEnvelope(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)
    data: list[T]
    pagination: Pagination


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: object | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
```

### `apps/api/src/fragwise_api/api/v1/schemas/__init__.py`

> **R3 KNOWN FOLLOW-UP — schemas import cycle.** The bottom-of-module
> `from .fragrance import FragranceListItem` pattern below works *iff*
> `fragrance.py` does not import from any detail-schema module at the top
> level. As written, `fragrance.py` imports `BrandSummary`, `PerfumerSummary`,
> `NoteSummary`, `AccordSummary`, `ConcentrationSummary`, `ArticleSummary`
> from sibling modules at the top — that re-creates a cycle. **The implementer
> must resolve this at apply time** by either (a) moving all `*Summary`
> classes to a new `schemas/summaries.py` module that imports nothing from
> sibling modules, then having both `fragrance.py` and the detail modules
> import from `summaries.py`, or (b) using string forward refs in
> `fragrance.py` for the summary types and rebuilding them via the
> `__init__.py` loop. (a) is the cleaner refactor; pick (a) and update the
> import lines accordingly. The pattern below remains the orchestration
> spine; only the *layout* of which module owns what changes. `pytest`
> will surface this immediately on first import.

```python
"""Centralized forward-ref resolution for v1 schemas (R2-C2).

R2-C2 design notes:
1. Pydantic v2's `_types_namespace=` kwarg is private — behavior varies
   across patch releases. Pydantic resolves forward refs against
   `module.__dict__` FIRST, so a kwarg-supplied dict cannot reliably
   override that. Each detail-schema module must instead `from .fragrance
   import FragranceListItem` at the bottom of its own module to populate
   its `globals()`.
2. `model_rebuild()` may raise `PydanticUserError` on classes that have no
   forward refs to resolve. We use `force=True` for idempotent re-imports
   AND we DROP `FragranceListItem` from the rebuild loop (it has no
   forward refs to resolve — all its imports are concrete).

Order: `fragrance` first (no forward refs), then detail modules. Each
detail module already imports FragranceListItem at the bottom for
forward-ref resolution.
"""

from __future__ import annotations

# Import every schema module first so all classes are defined.
from . import accord, article, brand, common, concentration, fragrance, note, perfumer

# Use force=True so re-imports are idempotent (R2-C2). Drop _types_namespace
# entirely — each module now exposes FragranceListItem in its own globals().
# Drop FragranceListItem from the loop; it has no forward refs.
for _model in (
    brand.BrandDetail,
    note.NoteDetail,
    note.NoteTreeNode,
    perfumer.PerfumerDetail,
    accord.AccordDetail,
    article.ArticleDetail,
    concentration.ConcentrationDetail if hasattr(concentration, "ConcentrationDetail") else None,
):
    if _model is not None:
        _model.model_rebuild(force=True)
```

### `apps/api/src/fragwise_api/api/v1/schemas/brand.py`

```python
"""Brand schemas. Forward-ref to FragranceListItem resolved in schemas/__init__.py."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .common import ListEnvelope


class BrandSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str


class BrandDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    fragrances: "ListEnvelope[FragranceListItem]"  # forward ref; resolved centrally


# R2-C2: Place FragranceListItem in this module's globals() so Pydantic's
# `eval_type_lenient` finds it via `module.__dict__` during model_rebuild().
# Pydantic v2 resolves forward refs against the OWNING module's namespace
# first, NOT a kwarg-supplied dict. Without this import, the centralized
# rebuild fails on patch-version differences in Pydantic.
from .fragrance import FragranceListItem  # noqa: F401, E402

# DO NOT call `model_rebuild()` here. See schemas/__init__.py (R2-C2 fix).
```

(`perfumer.py`, `accord.py`, `article.py`, `note.py`, `concentration.py`
follow the same shape: `Summary` with `slug`/`name` (article: `slug`/`title`/
`published_at`), `Detail` with the same plus `"ListEnvelope[FragranceListItem]"`
forward ref. **Each detail-schema module that uses the
`"ListEnvelope[FragranceListItem]"` forward ref MUST also add the same
`from .fragrance import FragranceListItem  # noqa: F401, E402` import at the
very bottom of the module.** None of them call `model_rebuild()` at module
bottom — that happens once in `schemas/__init__.py`.)

### `apps/api/src/fragwise_api/api/v1/schemas/note.py`

```python
"""Note schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .common import ListEnvelope


class NoteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str


class NoteTreeNode(BaseModel):
    """Self-recursive tree node used by GET /api/v1/notes."""

    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    # R2-C2 hygiene: use Field(default_factory=list) instead of `= []` to
    # avoid the mutable-default-argument pitfall on a recursive model.
    children: list["NoteTreeNode"] = Field(default_factory=list)


class NoteTreeEnvelope(BaseModel):
    data: list[NoteTreeNode]


class NoteDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    parent: NoteSummary | None
    fragrances: "ListEnvelope[FragranceListItem]"


# R2-C2: place FragranceListItem in this module's globals() so Pydantic's
# eval_type_lenient finds it via module.__dict__ during model_rebuild().
from .fragrance import FragranceListItem  # noqa: F401, E402

# DO NOT call `model_rebuild()` here. See schemas/__init__.py.
```

### `apps/api/src/fragwise_api/api/v1/schemas/fragrance.py`

```python
"""Fragrance schemas. `id` is a UUID; Pydantic v2 serializes to string in JSON."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .accord import AccordSummary
from .article import ArticleSummary
from .brand import BrandSummary
from .concentration import ConcentrationSummary
from .note import NoteSummary
from .perfumer import PerfumerSummary


class NotesByRole(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    top: list[NoteSummary] = []
    heart: list[NoteSummary] = []
    base: list[NoteSummary] = []


class FragranceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID                        # C4: was `str`; ORM column is uuid.UUID
    slug: str
    name: str
    brand: BrandSummary
    year_released: int | None
    gender: str
    concentration: ConcentrationSummary | None


class FragranceDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID                        # C4
    slug: str
    name: str
    description: str | None
    year_released: int | None
    year_text: str | None
    gender: str
    brand: BrandSummary
    concentration: ConcentrationSummary | None
    perfumers: list[PerfumerSummary]
    notes: NotesByRole
    accords: list[AccordSummary]
    articles: list[ArticleSummary]


def map_fragrance_detail(frag: object) -> FragranceDetail:
    """Build FragranceDetail from an eager-loaded Fragrance ORM object.

    `frag.fragrance_notes` is the list of FragranceNote association rows
    (eager-loaded via selectinload(Fragrance.fragrance_notes).selectinload(
    FragranceNote.note)). Group by `role` for the response shape. C4: do NOT
    convert `id` with str(); Pydantic v2 handles UUID -> string serialization.
    """
    by_role: dict[str, list[NoteSummary]] = {"top": [], "heart": [], "base": []}
    for fn in frag.fragrance_notes:  # type: ignore[attr-defined]
        by_role[fn.role.value].append(NoteSummary.model_validate(fn.note))
    return FragranceDetail(
        id=frag.id,  # type: ignore[attr-defined]      # UUID, not str
        slug=frag.slug,  # type: ignore[attr-defined]
        name=frag.name,  # type: ignore[attr-defined]
        description=frag.description,  # type: ignore[attr-defined]
        year_released=frag.year_released,  # type: ignore[attr-defined]
        year_text=frag.year_text,  # type: ignore[attr-defined]
        gender=frag.gender.value,  # type: ignore[attr-defined]
        brand=BrandSummary.model_validate(frag.brand),  # type: ignore[attr-defined]
        concentration=(
            ConcentrationSummary.model_validate(frag.concentration)  # type: ignore[attr-defined]
            if frag.concentration is not None  # type: ignore[attr-defined]
            else None
        ),
        perfumers=[PerfumerSummary.model_validate(p) for p in frag.perfumers],  # type: ignore[attr-defined]
        notes=NotesByRole(**by_role),
        accords=[AccordSummary.model_validate(a) for a in frag.accords],  # type: ignore[attr-defined]
        articles=[ArticleSummary.model_validate(a) for a in frag.articles],  # type: ignore[attr-defined]
    )
```

**Cross-cutting note (C4)**: across `BrandSummary`, `PerfumerSummary`,
`NoteSummary`, `AccordSummary`, `ConcentrationSummary`, `ArticleSummary`,
`BrandDetail`, `PerfumerDetail`, `NoteDetail`, `AccordDetail`, `ArticleDetail`
— none of them carry an `id` field today. Only `FragranceListItem` and
`FragranceDetail` expose `id`. Both are now `UUID`. The OpenAPI schema notes
`id` is a UUID v7 string in JSON; clients can treat it as opaque.

### `apps/api/src/fragwise_api/api/v1/routers/fragrances.py`

```python
"""GET /api/v1/fragrances and /api/v1/fragrances/{slug}."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload, selectinload

from fragwise_api.db.models import (
    Accord,
    Brand,
    Concentration,
    Fragrance,
    FragranceAccord,
    FragranceNote,
    FragrancePerfumer,
    Note,
    Perfumer,
)

from ..deps import DbSession
from ..errors import not_found
from ..filters import FragranceListQueryDep
from ..pagination import paginate
from ..schemas.common import ListEnvelope, Pagination
from ..schemas.fragrance import FragranceDetail, FragranceListItem, map_fragrance_detail

router = APIRouter(prefix="/fragrances", tags=["Fragrances"])

SLUG = Annotated[str, Path(pattern=r"^[a-z0-9-]+$")]


def _apply_filters(stmt: Select[tuple[Fragrance]], f) -> Select[tuple[Fragrance]]:
    """Compose WHERE clauses for FragranceListQuery.

    C3: Multi-value M:M filters (perfumer, accord, note) MUST use a subquery
    of association-table IDs, NOT a JOIN + DISTINCT. The JOIN+DISTINCT pattern
    multiplies rows when a fragrance has multiple matching tags, breaking
    pagination LIMIT semantics. The IN-subquery pattern keeps the row set
    distinct without a global `.distinct()` and avoids expensive plan blowups
    on large catalogs.

    R2-C5: Strip empty strings from multi-value list filters so `?accord=`
    (no value) or trailing-comma typos like `?accord=woody,` don't reduce
    results to zero via `Accord.slug.in_([""])`. We chose the strip-empty
    approach over `Annotated[str, StringConstraints(min_length=1)]` field
    types: more permissive, fewer false 422s for trailing-comma typos. If
    every element is empty after stripping, the filter is treated as absent.

    R3 fix: compute locals instead of mutating the Pydantic input model.
    Mutating `f` is fragile under future hardening (`frozen=True`,
    `validate_assignment=True`) and conflates filter normalization with
    schema validation.
    """
    # Compute normalized locals (R3) — do not mutate `f`.
    accord = [s for s in (f.accord or []) if s]
    perfumer = [s for s in (f.perfumer or []) if s]
    note = [s for s in (f.note or []) if s]

    if f.brand is not None:
        stmt = stmt.join(Brand, Brand.id == Fragrance.brand_id).where(Brand.slug == f.brand)
    if f.gender is not None:
        stmt = stmt.where(Fragrance.gender == f.gender)
    if f.year_min is not None:
        stmt = stmt.where(Fragrance.year_released >= f.year_min)
    if f.year_max is not None:
        stmt = stmt.where(Fragrance.year_released <= f.year_max)
    if f.concentration is not None:
        stmt = stmt.join(Concentration, Concentration.id == Fragrance.concentration_id).where(
            Concentration.slug == f.concentration
        )
    if perfumer:
        stmt = stmt.where(
            Fragrance.id.in_(
                select(FragrancePerfumer.fragrance_id).where(
                    FragrancePerfumer.perfumer_id.in_(
                        select(Perfumer.id).where(Perfumer.slug.in_(perfumer))
                    )
                )
            )
        )
    if accord:
        stmt = stmt.where(
            Fragrance.id.in_(
                select(FragranceAccord.fragrance_id).where(
                    FragranceAccord.accord_id.in_(
                        select(Accord.id).where(Accord.slug.in_(accord))
                    )
                )
            )
        )
    if note:
        stmt = stmt.where(
            Fragrance.id.in_(
                select(FragranceNote.fragrance_id).where(
                    FragranceNote.note_id.in_(
                        select(Note.id).where(Note.slug.in_(note))
                    )
                )
            )
        )
    return stmt  # NO global .distinct() — IN-subqueries already deduplicate


@router.get("", response_model=ListEnvelope[FragranceListItem])
async def list_fragrances(
    session: DbSession,
    query: FragranceListQueryDep,
) -> ListEnvelope[FragranceListItem]:
    stmt = (
        select(Fragrance)
        .options(joinedload(Fragrance.brand), joinedload(Fragrance.concentration))
        .order_by(Fragrance.name.asc(), Fragrance.id.asc())  # S5: stable tiebreaker
    )
    stmt = _apply_filters(stmt, query)
    rows, total = await paginate(
        session, stmt, limit=query.limit, offset=query.offset
    )
    return ListEnvelope[FragranceListItem](
        data=[FragranceListItem.model_validate(r) for r in rows],
        pagination=Pagination(
            limit=query.limit,
            offset=query.offset,
            total=total,
            has_next=query.offset + query.limit < total,
        ),
    )


@router.get("/{slug}", response_model=FragranceDetail)
async def get_fragrance(session: DbSession, slug: SLUG) -> FragranceDetail:
    stmt = (
        select(Fragrance)
        .where(Fragrance.slug == slug)
        .options(
            joinedload(Fragrance.brand),
            joinedload(Fragrance.concentration),
            selectinload(Fragrance.perfumers),
            selectinload(Fragrance.fragrance_notes).selectinload(FragranceNote.note),
            selectinload(Fragrance.accords),
            selectinload(Fragrance.articles),
        )
    )
    frag = (await session.execute(stmt)).scalars().unique().one_or_none()
    if frag is None:
        raise not_found("Fragrance", slug)
    return map_fragrance_detail(frag)
```

### `apps/api/src/fragwise_api/api/v1/routers/articles.py`

```python
"""Articles list uses Article.title (no `name` column). W5 fix."""

from sqlalchemy import select
from sqlalchemy.orm import joinedload

# ... inside list handler:
stmt = (
    select(Article)
    .order_by(Article.title.asc(), Article.id.asc())  # title, then UUID v7 tiebreaker
)
```

### `apps/api/src/fragwise_api/api/v1/routers/brands.py` (R2-W2 — ILIKE escape)

```python
"""Brands list with `?q=` substring filter. R2-W2: escape `%` and `_`
in user input so `?q=%` does not match every row.
"""

from sqlalchemy import select
from fastapi import APIRouter

from ..deps import DbSession
from ..filters import BrandListQueryDep
from ..pagination import paginate
from ..schemas.brand import BrandSummary
from ..schemas.common import ListEnvelope, Pagination
from fragwise_api.db.models import Brand

router = APIRouter(prefix="/brands", tags=["Brands"])


@router.get("", response_model=ListEnvelope[BrandSummary])
async def list_brands(
    session: DbSession,
    q: BrandListQueryDep,  # R3: Annotated[BrandListQuery, Query()]; matches FragranceListQueryDep
) -> ListEnvelope[BrandSummary]:
    stmt = select(Brand).order_by(Brand.name.asc(), Brand.id.asc())
    if q.q:
        # R2-W2: escape ILIKE wildcards in user input so `%` and `_` from
        # `?q=%` cannot act as glob characters and match every row. Order
        # matters: escape the backslash FIRST (otherwise the later `\\%`
        # we insert would itself get escaped), then the SQL wildcards.
        escaped = (
            q.q.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        stmt = stmt.where(Brand.name.ilike(f"%{escaped}%", escape="\\"))
    rows, total = await paginate(
        session, stmt, limit=q.limit, offset=q.offset
    )
    data = [BrandSummary.model_validate(r) for r in rows]
    return ListEnvelope[BrandSummary](
        data=data,
        pagination=Pagination(
            limit=q.limit, offset=q.offset, total=total,
            has_next=q.offset + q.limit < total,
        ),
    )
```

(Other routers — `perfumers.py`, `accords.py`, `notes.py`, `articles.py` —
follow the same pattern: typed deps using their combined `*ListQuery` model,
default sort `name ASC`/`title ASC` + `id ASC`, `not_found(...)` on missing
slug. **`perfumers.py` MUST apply the same R2-W2 ILIKE escape on
`Perfumer.name`** for the `?q=` substring filter. Detail routes with a
paginated nested `fragrances` array use plain `LimitOffsetParams` (no
filters) and call `paginate(... limit=..., offset=...)` — the `pk_column` parameter was removed in the R3 surgical fix; counting rows of the filtered subquery is sufficient.
`notes.py` differs: list returns the tree (no pagination), detail returns
`parent` + paginated fragrances.)

### `apps/api/src/fragwise_api/main.py` (modifications)

```python
"""FastAPI app factory + lifespan + /healthz + /readyz + /api/v1."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from fragwise_api.api.v1 import api_router
from fragwise_api.api.v1.errors import install_error_handlers
from fragwise_api.db.session import make_engine, make_sessionmaker

logger = logging.getLogger(__name__)

# Pinned (ADR-0022): NOT derived from pyproject.version. Bump deliberately.
OPENAPI_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Single source of truth for the engine + sessionmaker (S6)."""
    engine = make_engine()
    app.state.db_engine = engine
    app.state.db_sessionmaker = make_sessionmaker(engine)
    try:
        yield
    finally:
        await engine.dispose()


def _resolve_cors_origins() -> list[str]:
    """ADR-0024: precedence CORS_ALLOW_ORIGIN, then NEXT_PUBLIC_API_URL, then *.

    Comma-separated values are split + stripped (e.g.
    `https://fragwise.app,https://staging.fragwise.app`).

    R2-W1: if the parsed origins list is empty (e.g. raw was `" , "` or
    only whitespace/commas), fall back to `["*"]`. An empty `allow_origins`
    list rejects ALL preflight requests, breaking the web client without
    any visible error in dev.
    """
    raw = (
        os.environ.get("CORS_ALLOW_ORIGIN")
        or os.environ.get("NEXT_PUBLIC_API_URL")
        or "*"
    )
    parsed = [o.strip() for o in raw.split(",") if o.strip()]
    return parsed or ["*"]  # final fallback if everything was whitespace/empty


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fragwise API",
        version=OPENAPI_VERSION,
        lifespan=lifespan,
        redirect_slashes=False,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_resolve_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )

    install_error_handlers(app)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> Any:
        """Readiness probe. S7: error message is generic; full exception is
        logged server-side (logger.exception) so connection strings, hostnames,
        or driver-leaked credentials never reach the response body."""
        sm = app.state.db_sessionmaker
        try:
            async with sm() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception:
            logger.exception("readyz: database probe failed")
            return JSONResponse(
                status_code=503,
                content={"status": "unready", "error": "database unreachable"},
            )

    app.include_router(api_router)
    return app


app = create_app()
```

### `apps/api/scripts/emit_openapi.py`

```python
"""Emit a deterministic apps/api/openapi.json from app.openapi()."""

from __future__ import annotations

import json
from pathlib import Path

from fragwise_api.main import app


def emit() -> None:
    schema = app.openapi()
    encoded = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    target = Path(__file__).resolve().parents[1] / "openapi.json"
    target.write_bytes(encoded)


if __name__ == "__main__":
    emit()
```

### Migration: `apps/api/alembic/versions/0002_fragrance_accords.py`

```python
"""fragrance_accords join

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fragrance_accords",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fragrance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fragrances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "accord_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accords.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "fragrance_id", "accord_id", name="uq_fragrance_accords_fid_aid"
        ),
    )
    op.create_index(
        "ix_fragrance_accords_fragrance_id", "fragrance_accords", ["fragrance_id"]
    )
    op.create_index(
        "ix_fragrance_accords_accord_id", "fragrance_accords", ["accord_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_fragrance_accords_accord_id", table_name="fragrance_accords")
    op.drop_index("ix_fragrance_accords_fragrance_id", table_name="fragrance_accords")
    op.drop_table("fragrance_accords")
```

## ORM Additions (Exact Lines)

### `apps/api/src/fragwise_api/db/models/joins.py` — add `FragranceAccord`

```python
class FragranceAccord(UUIDMixin, Base):
    __tablename__ = "fragrance_accords"

    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fragrances.id", ondelete="CASCADE"),
        nullable=False,
    )
    accord_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accords.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "fragrance_id", "accord_id", name="uq_fragrance_accords_fid_aid",
        ),
        Index("ix_fragrance_accords_fragrance_id", "fragrance_id"),
        Index("ix_fragrance_accords_accord_id", "accord_id"),
    )
```

`FragranceNote` MUST gain a `note: Mapped["Note"] = relationship(lazy="raise_on_sql")` to support the eager-load chain.

### `apps/api/src/fragwise_api/db/models/fragrance.py` — add (after existing fields)

```python
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy

# ... inside Fragrance:
    fragrance_notes: Mapped[list["FragranceNote"]] = relationship(
        back_populates="fragrance",
        lazy="raise_on_sql",
        cascade="all, delete-orphan",
        overlaps="notes",  # symmetric with Fragrance.notes (plain view via secondary)
    )
    # Plain access view of notes via the association object (C2 pattern).
    # The "real" relationship that owns the cascade is `fragrance_notes`; the
    # plain `notes` view is read-only and `overlaps=` silences the legitimate
    # mapper warning that two relationships read the same FK columns.
    notes: Mapped[list["Note"]] = relationship(
        secondary="fragrance_notes",
        viewonly=True,
        overlaps="fragrance_notes,note",
        lazy="raise_on_sql",
    )
    perfumers: Mapped[list["Perfumer"]] = relationship(
        secondary="fragrance_perfumers",
        back_populates="fragrances",
        lazy="raise_on_sql",
    )
    accords: Mapped[list["Accord"]] = relationship(
        secondary="fragrance_accords",
        back_populates="fragrances",
        lazy="raise_on_sql",
    )
    articles: Mapped[list["Article"]] = relationship(
        secondary="fragrance_articles",
        back_populates="fragrances",
        lazy="raise_on_sql",
    )
```

### Association-object overlap pattern (C2)

The spec requires `Note.fragrances` and `Fragrance.notes` to behave as plain
M:M views, but the underlying relationship `Fragrance.fragrance_notes ↔
Note.fragrance_notes` is an **association object** (`FragranceNote` carries
the `role` enum). Defining `Note.fragrances = relationship(secondary=
"fragrance_notes", back_populates="notes")` alongside the association object
trips a SQLAlchemy mapper-configure error or — worse — a silent overlap
warning that masks data corruption.

The fix: every "plain view" M:M relationship that uses `secondary=` over a
table that is **also** mapped as an association object MUST be declared with:

- `viewonly=True` — declares the relationship as read-only at the ORM layer
- `overlaps="<association_attr>,<inverse_assoc_attr>"` — silences the mapper
  warning by acknowledging that this relationship overlaps with the
  association object on the same FK columns

Apply this pattern on (R2-C3 — the symmetric back-refs on the association
object MUST also declare `overlaps`, otherwise SQLAlchemy still warns and
mapper config is incomplete):

| Relationship | viewonly | overlaps |
|---|---|---|
| `Fragrance.notes` (plain via `secondary`) | yes | `"fragrance_notes,note"` |
| `Fragrance.fragrance_notes` (association objects) | no | `"notes"` |
| `FragranceNote.note` (assoc-obj forward ref) | no | `"notes"` |
| `FragranceNote.fragrance` (assoc-obj reverse) | no | `"fragrance_notes"` (different path from `Fragrance.notes` via secondary) |
| `Note.fragrance_notes` (reverse on assoc-obj) | yes | `"fragrances"` |
| `Note.fragrances` (plain via `secondary`) | yes | `"fragrance_notes,fragrance"` |

| Side | Relationship | secondary | viewonly |
|------|--------------|-----------|----------|
| `Fragrance.perfumers`, `Perfumer.fragrances` | Plain M:M (no association object) | `fragrance_perfumers` | no |
| `Fragrance.accords`, `Accord.fragrances` | Plain M:M (no association object) | `fragrance_accords` | no |
| `Fragrance.articles`, `Article.fragrances` | Plain M:M (no association object) | `fragrance_articles` | no |

#### `FragranceNote` — additions to merge into the existing class

> **DO NOT replace the existing `FragranceNote` class wholesale.** The current
> class in `apps/api/src/fragwise_api/db/models/joins.py` already declares
> `position`, MRO `(UUIDMixin, Base)`, and `__table_args__` with
> `UniqueConstraint("fragrance_id", "note_id", "role")` plus two indexes
> (`ix_fragrance_notes_fragrance_id`, `ix_fragrance_notes_note_id`). Preserve
> all of those. Only **add** the two relationships below; do **not** drop
> `position` or the indexes.

```python
# ADD inside the existing FragranceNote class:
fragrance: Mapped["Fragrance"] = relationship(
    back_populates="fragrance_notes",
    lazy="raise_on_sql",
    overlaps="fragrance_notes",
)
note: Mapped["Note"] = relationship(
    back_populates="fragrance_notes",
    lazy="raise_on_sql",
    overlaps="notes",
)
```

`Brand.fragrances`, `Perfumer.fragrances`, `Accord.fragrances`,
`Article.fragrances`, `Note.fragrances` (via `fragrance_notes` secondary, with
the overlap pattern above) all set `lazy="raise_on_sql"`. `Note.parent` and
`Note.children` self-ref use `remote_side=[Note.id]` / `back_populates`.

### Hierarchical notes loader depth (S1 + R2-C4)

`Note.children` is a self-referential relationship (`parent_id` self-FK on
`notes`). The `GET /api/v1/notes` tree handler MUST eager-load multiple levels;
SQLAlchemy 2.0+ supports `recursion_depth` on `selectinload` for self-ref
relationships, **but `recursion_depth=N` is only valid when the relationship
itself declares `join_depth=N`** — without `join_depth`, SQLAlchemy raises
`ArgumentError: recursion_depth is only valid for self-referential eager
loaders`. (R2-C4)

#### `Note` — additions to merge into the existing class

> **DO NOT replace the existing `Note` class wholesale.** The current class
> at `apps/api/src/fragwise_api/db/models/note.py` already declares
> `parent_id` with `ondelete="RESTRICT"`, MRO `(UUIDMixin, TimestampMixin,
> Base)`, and `__table_args__` containing `Index("ix_notes_slug", "slug",
> unique=True)` and `Index("ix_notes_parent_id", "parent_id")`. Preserve all
> of those. Only **add** the four relationships below.

```python
# ADD inside the existing Note class:
parent: Mapped["Note | None"] = relationship(
    "Note",
    remote_side="Note.id",
    back_populates="children",
    lazy="raise_on_sql",
)
children: Mapped[list["Note"]] = relationship(
    "Note",
    back_populates="parent",
    lazy="raise_on_sql",
    join_depth=10,  # belt-and-suspenders for any joinedload use; selectinload's
                    # `recursion_depth` parameter does not strictly require it
                    # but SQLAlchemy versions vary — keep for robustness.
)

fragrance_notes: Mapped[list["FragranceNote"]] = relationship(
    back_populates="note",
    viewonly=True,
    lazy="raise_on_sql",
    overlaps="fragrances",
)
fragrances: Mapped[list["Fragrance"]] = relationship(
    secondary="fragrance_notes",
    viewonly=True,
    lazy="raise_on_sql",
    overlaps="fragrance_notes,fragrance",
)
```

#### Notes router list handler

```python
# inside notes router list handler:
stmt = (
    select(Note)
    .where(Note.parent_id.is_(None))                  # roots only
    .options(selectinload(Note.children, recursion_depth=10))
    .order_by(Note.name.asc(), Note.id.asc())
)
```

The integration test for `GET /api/v1/notes` MUST assert that a depth-2+
descendant (e.g. `citrus → bergamot → bergamot-mint` if seeded) appears in the
tree response — guarding against silent depth-1 truncation.

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | Pydantic schema rebuild + mapper | Plain pytest, no DB |
| Integration | Routes, filters, pagination, eager-load | testcontainers Postgres + Alembic upgrade + httpx ASGITransport |
| Integration | Query count ≤ 6 on detail (S3) | `event.listens_for(engine.sync_engine, "after_cursor_execute")` increments a counter; assert ≤ 6 |
| Drift gate | OpenAPI byte-equality | `apps/api/tests/integration/api/v1/test_openapi_drift.py` re-emits and `assert committed == live_bytes` |

### Query-count fixture (paste-ready)

```python
# apps/api/tests/integration/api/v1/conftest.py (excerpt)
import pytest
from sqlalchemy import event

@pytest.fixture()
def query_counter(engine):
    counts = {"selects": 0}

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def _on_exec(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            counts["selects"] += 1

    yield counts
    event.remove(engine.sync_engine, "after_cursor_execute", _on_exec)
```

### Test files

- `test_fragrances_list.py` — pagination; brand+gender filter; multi-accord OR; multi-note OR; year range; empty result; 422 on invalid limit; stable-sort tiebreaker (S5: insert two same-name fragrances and assert page-boundary order is consistent)
- `test_fragrances_detail.py` — happy path with all nested fields; `query_counter["selects"] <= 6` (S3); 404
- `test_brands.py`, `test_perfumers.py` — list+detail happy + 404 + `?q=` substring filter
- `test_accords.py`, `test_articles.py` — list+detail happy + 404
- `test_notes.py` — tree shape with depth-2+ descendants visible (S1); detail with parent + paginated fragrances
- `test_envelope.py` — 422 envelope shape (and that `input`/`ctx` are NOT in the response — W7); 404 envelope shape; 405 envelope (`code: method_not_allowed`); 500 envelope (force via monkeypatched session)
- `test_openapi_drift.py` — emit deterministic bytes; assert equal to committed
- `test_trailing_slash.py` — `/api/v1/fragrances/` returns 404 with no `Location`
- `test_cors.py` — OPTIONS preflight returns `Access-Control-Allow-Origin`; verify lookup precedence by setting `NEXT_PUBLIC_API_URL=https://fragwise.app` and asserting the header echoes that origin

Seed fixture (mini set, predictable assertions): 2 brands × ~3 frags each, 2 perfumers, 6 accords, ~10 notes (with parent/child at ≥2 depth), 2 articles, FragranceAccord rows wired.

## CI: OpenAPI Drift Gate (`.github/workflows/api.yml` addition)

```yaml
      - name: Emit OpenAPI
        run: uv run python scripts/emit_openapi.py

      - name: OpenAPI drift gate
        run: |
          if ! git diff --exit-code apps/api/openapi.json; then
            echo "::error::apps/api/openapi.json is stale. Run 'just emit-openapi' and commit the diff."
            exit 1
          fi
```

## Justfile Recipe

```
# Emit a deterministic apps/api/openapi.json snapshot.
emit-openapi:
    cd apps/api && uv run python scripts/emit_openapi.py
```

## Pyproject + Lockfile

W3: pin **exact** patch versions of `fastapi` and `pydantic` in
`apps/api/pyproject.toml [project] dependencies` (e.g. `fastapi==0.128.0`,
`pydantic==2.10.4`) — not `>=` ranges. Static OpenAPI byte-equality is
fragile across patch bumps; pinning gives a single deliberate upgrade path.
A `uv lock --upgrade fastapi pydantic` MUST be followed by `just emit-openapi`
and a committed `apps/api/openapi.json` diff.

No new runtime deps. `orjson` is **not** required: `json.dumps(..., sort_keys=True, separators=(",", ":"))` is sufficient for byte-deterministic emission and removes one dependency.

## Cross-Cutting Notes

- **Trailing slashes**: `redirect_slashes=False` in `FastAPI(...)`. All routes declared without trailing slash. `/api/v1/fragrances/` returns 404 (verified by integration test).
- **Error code taxonomy** (closed): `not_found` (404), `method_not_allowed` (405), `conflict` (409), `invalid_params` (422), `http_error` (other 4xx), `internal_error` (5xx). Add new codes only with a spec delta. Mapping is implemented by `_code_for_status()` in `errors.py` (W1).
- **Validation error filtering (W7)**: the `RequestValidationError` handler keeps only `loc`, `msg`, `type` per error dict; `input` and `ctx` are dropped to avoid reflecting user-supplied data in the response.
- **CORS preflight**: `CORSMiddleware` with `allow_methods=["GET", "OPTIONS"]`. Origin precedence: `CORS_ALLOW_ORIGIN`, then `NEXT_PUBLIC_API_URL`, then `*` in dev. Comma-separated lists are split into `allow_origins`. Documented in `.env.example` (ADR-0024).
- **Articles relationship**: the `fragrance_articles` join already exists in `0001_initial`. Adding `Fragrance.articles = relationship(secondary="fragrance_articles", ...)` is ORM-only; no migration needed.
- **`/healthz` and `/readyz`**: unchanged URLs; remain at root, NOT under `/api/v1`. `readyz` returns a generic `database unreachable` message and logs the full exception via `logger.exception` (S7).
- **Seed YAML extension (S4 + R2-W5)**: `data/seed/minimal_fragrances.yaml` gains an optional `accords:` array (list of accord slugs) per fragrance. `data/scripts/seed_minimal_fragrances.py` upserts `fragrance_accords` rows in pass 3 (alongside notes/perfumers), keyed on `(fragrance_id, accord_id)`. **Additionally (R2-W5)**: the seed must include a depth-2 note hierarchy (e.g. `citrus → bergamot → bergamot-mint`) so the `test_notes.py` tree-shape assertion can verify that `selectinload(Note.children, recursion_depth=10)` actually returns a 2+ level nested structure. Without seeded depth-2 data, the S1 fix is untestable. Both pieces are in scope for P1 — without them the integration tests for `accord` filters and the notes tree cannot load valid fixtures.

## Migration / Rollout

1. Apply `0002_fragrance_accords` to dev DB (`alembic upgrade head`).
2. **S4 — in-scope sub-task for P1, NOT a separate change.** Extend
   `data/seed/minimal_fragrances.yaml` schema with `accords:` array; update
   `data/scripts/seed_minimal_fragrances.py` to upsert `fragrance_accords`
   rows. **R2-W5**: also add a depth-2 note hierarchy in
   `data/seed/minimal_fragrances.yaml` (or a new `data/seed/notes.yaml` —
   implementer's call) — e.g. `citrus → bergamot → bergamot-mint`. The
   integration test `test_notes.py` (or a dedicated `test_notes_tree.py`)
   asserts the depth-2 descendant is present in the tree response,
   guarding against silent depth-1 truncation in the `selectinload(...,
   recursion_depth=10)` chain (S1 + R2-C4). The S1 fix is meaningless
   without a seeded depth-2 fixture.
3. Land routers + tests behind no flag (additive).
4. Commit `apps/api/openapi.json`; CI gate becomes active.
5. Rollback path: `alembic downgrade -1` drops `fragrance_accords`; routes are read-only — no data corruption risk.

## Open Questions

- [ ] Sort knob: ship `?sort=` whitelist now or defer until catalog UI lands? Design currently defers (lock `name ASC` + `id ASC` tiebreaker); flagging for `judgment-day` review.

## Process Gates

- [x] `judgment-day` adversarial review of THIS design file (3 rounds; ESCALATED-WITH-CARVEOUTS — 2 CRITICALs surgically fixed in design, smaller items deferred to apply phase per "Known follow-ups" below)
- [ ] After `sdd-apply`: `sdd-verify` runs the full integration suite + OpenAPI drift gate
- [ ] Archive only after CI green on the PR

## Known Follow-ups for Apply Phase

These are issues that judgment-day surfaced but cannot be fully resolved without running code. The implementer MUST verify each during `sdd-apply` and fix in-place. Each item has a precise diagnosis and recommended fix shape; pytest will surface any remaining drift.

### F1 — schemas import cycle (R3-C2, deferred to apply)

The current schema layout has `fragrance.py` importing `*Summary` types from sibling detail modules at the top, while detail modules import `FragranceListItem` from `fragrance.py` at the bottom. This is a circular import that will fail at first `pytest` run.

- **File**: `apps/api/src/fragwise_api/api/v1/schemas/`
- **Recommended fix**: move all `*Summary` classes (`BrandSummary`, `PerfumerSummary`, `NoteSummary`, `AccordSummary`, `ConcentrationSummary`, `ArticleSummary`) to a new `schemas/summaries.py`. Both `fragrance.py` and the detail modules then import from `summaries.py` (which imports nothing from sibling modules). The bottom-of-module `from .fragrance import FragranceListItem` pattern stays — it's only the summary side that needs to break the cycle.
- **Verification**: `cd apps/api && uv run python -c "from fragwise_api.api.v1 import schemas"` exits 0.
- **Test gate**: any vitest/pytest failure with `ImportError: cannot import name from partially initialized module` points here.

### F2 — paste-ready Note + FragranceNote merge guidance (R3 carry)

The existing ORM classes already have columns/indexes/`ondelete` settings the design's "additions" must NOT clobber. The merge boxes above include explicit DO-NOT-REPLACE callouts. During apply, double-check by `git diff apps/api/src/fragwise_api/db/models/note.py` and `joins.py` after edits — the diffs should be additive (new relationship attributes only); no removals of `position`, indexes, or `ondelete="RESTRICT"`.

### F3 — `FragranceNote.fragrance` overlaps may be insufficient

The 6-row overlaps table sets `FragranceNote.fragrance overlaps="fragrance_notes"`. SQLAlchemy may still emit a warning that `Fragrance.notes` (via secondary) overlaps with `FragranceNote.fragrance` on the same FK columns. If `configure_mappers()` warns at app startup, extend to `overlaps="fragrance_notes,notes"`.

- **Verification**: at app boot (or in a test fixture), call `Base.registry.configure()` and assert no `SAWarning` is emitted. If one fires, append the missing overlap target.

### F4 — `_validation_exception_handler` body-error filtering

P1 is read-only (GET only), so `RequestValidationError` only fires on path/query params; `loc[0]` is always `query` or `path`. If a future phase adds POST/PUT and the same handler runs, body errors include input shape via `loc` indices. Already partially mitigated (we strip `input` and `ctx`), but verify the filter is sufficient when the first POST endpoint lands (Phase 2 `/search`).

### F5 — `BrandFilters.q` ILIKE escape order edge cases

Add unit tests in `test_brands.py`: `?q=%`, `?q=_`, `?q=foo\bar`, `?q=50%`. Each must return zero rows (no row literally contains those characters in the seeded brand names). If any returns the full catalog, the escape pattern is broken.

### F6 — CORS allow_credentials tripwire

The `_resolve_cors_origins()` final fallback returns `["*"]`. This is only valid because `allow_credentials=False`. If a future change enables credentials, `*` must be replaced with explicit dev origins. Add a comment in `main.py` near the middleware setup to surface this.

### F7 — `Note.children` `join_depth` rationale

The comment justifies `join_depth=10` as "required for `selectinload(..., recursion_depth=10)`". This is imprecise — `recursion_depth` may work without it on current SQLAlchemy patches. Keep `join_depth=10` (harmless) but reword the comment to "belt-and-suspenders" if the implementer encounters no `ArgumentError` without it.

### F8 — Default sort knob (carry-forward Open Question)

The Phase 4 catalog UI may need `?sort=year_released DESC` or similar. Adding `?sort=` later is backwards-compatible (additive query param). Implementer: do NOT add it now; surface as Phase 1.5 / Phase 4 follow-up.

### F9 — OpenAPI byte-equality drift

`apps/api/openapi.json` will diff on any `fastapi`/`pydantic` patch bump. CI gate fails loudly. Fix: re-run `just emit-openapi` and commit. Document this in CONTRIBUTING.md.

---

**Bottom line for the implementer**: F1 is the one that will block the first test run. Do that refactor before anything else. F2-F9 surface during normal development and have one-line fixes.
