# Design: phase-0c-schema-and-ontology

## Technical Approach

This change lands the data foundation: SQLAlchemy 2.0 async typed-mapping
models, an Alembic environment configured for async, a single hand-written
initial migration that owns the `vector` extension, the HNSW index, the
FTS index, and the concentration lookup seed; an ontology package shape
that splits *data* (`packages/ontology/`) from *loader* (`apps/api/`); and
three operator scripts under `data/scripts/`. The lifespan hook in
`apps/api/src/fragwise_api/main.py` is wired to construct an
`AsyncEngine` and `async_sessionmaker`, store them on `app.state`, dispose
on shutdown, and a new `/readyz` endpoint runs `SELECT 1` through the
sessionmaker. Integration tests boot a `pgvector/pgvector:pg16`
testcontainer; an opt-in `integration` pytest marker keeps unit tests fast
and Docker-free by default.

Spec coverage: the `data-model` requirements drive `db/models/*` + the
`0001_initial.py` revision; `ingestion` drives `data/scripts/*`;
`api-app` drives `main.py` + `db/session.py` + `ontology/loader.py`;
`repo-skeleton` is satisfied by the file paths chosen below (no new
runtime decision).

## Versions Verified Via Context7 (2026-05-06)

| Package | Pin | Source |
|---|---|---|
| `sqlalchemy[asyncio]` | `>=2.0.40,<3.0` | SQLAlchemy 2.0 docs (`/websites/sqlalchemy_en_20`) |
| `asyncpg` | `>=0.30,<1.0` | matches SQLAlchemy 2.0 async examples |
| `alembic` | `>=1.14,<2.0` | Alembic cookbook (`/sqlalchemy/alembic`) |
| `pgvector` | `>=0.4,<1.0` | pgvector-python README (`/pgvector/pgvector-python`); `VECTOR` SQLAlchemy type, `postgresql_using='hnsw'` index API |
| `pydantic` | `>=2.10,<3.0` | already a transitive of FastAPI; promote to direct |
| `pyyaml` | `>=6.0,<7.0` | unchanged |
| `openai` | `>=1.55,<3.0` | OpenAI Python `v2.11.0` confirms `embeddings.create(input=[...], dimensions=512)` for `text-embedding-3-*` |
| `tenacity` | `>=9.0,<10.0` | unchanged |
| `uuid-utils` | `>=0.10,<1.0` | `uuid_utils.uuid7()` returns a stdlib-compatible `uuid.UUID`, sortable, maintained (`/aminalaee/uuid-utils`) |
| `python-slugify` | `>=8.0,<9.0` | only consumed by ingest/seed scripts |
| `testcontainers[postgres]` | `>=4.9,<5.0` | `PostgresContainer(image=..., driver="asyncpg")` + `get_connection_url()` (`/testcontainers/testcontainers-python`) |
| `types-pyyaml` | `>=6.0,<7.0` | dev dep |

Notable Context7 confirmations:
- pgvector exposes the SQLAlchemy `VECTOR` type and the idiomatic
  `Index(..., postgresql_using='hnsw', postgresql_with={'m': 16,
  'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})`
  pattern. We will use this via `op.create_index(...)` with the same
  kwargs, equivalent to a hand-written `CREATE INDEX ... USING hnsw`.
- Alembic cookbook documents `async_engine_from_config` +
  `asyncio.run(run_async_migrations())` as the canonical async env.
- `uuid_utils.uuid7()` returns objects naturally sortable; cast to
  `str(uuid_utils.uuid7())` for a stdlib-`uuid.UUID`-compatible string,
  or keep the object — SQLAlchemy's `UUID` type accepts both.

## Architecture Decisions

### ADR-0011: UUID v7 everywhere (Q1 lock-in)

**Choice**: All entity tables use `id UUID PRIMARY KEY`. Application
generates v7 UUIDs Python-side via `uuid_utils.uuid7()`; PG16 lacks
`uuidv7()` natively.
**Alternatives**: BIGSERIAL (loses fork-safe seed dumps); `pg_uuidv7`
extension (one more extension to manage on Neon); UUID v4 (loses index
locality).
**Rationale**: OSS forks need to dump-and-merge data. v7 keeps B-tree
locality close to v4-with-time-prefix and `uuid-utils` is fast (Rust).
**Implementation**: `db/base.py::UUIDMixin.id = mapped_column(UUID,
primary_key=True, default=lambda: uuid_utils.uuid7())`.

### ADR-0012: Async Alembic env.py

**Choice**: `env.py` uses `async_engine_from_config()` +
`asyncio.run(run_async_migrations())`.
**Alternatives**: Sync engine (battle-tested, but adds a second connection
style for no benefit).
**Rationale**: App is async; Context7 documents the canonical async
pattern. `psycopg` not used anywhere — a sync env would force adding it.

### ADR-0013: testcontainers > GH Actions postgres service

**Choice**: Tests boot `pgvector/pgvector:pg16` via testcontainers; same
fixture local + CI. Marker `@pytest.mark.integration` opt-in;
`addopts = "-m 'not integration'"` default.
**Alternatives**: GH `services.postgres` (different fixture local-vs-CI);
reuse compose postgres (test pollution).
**Rationale**: Single source of truth; CI runners ship Docker; marker
keeps unit tests fast on contributor machines without Docker.

### ADR-0014: Hand-written initial migration (no autogenerate)

**Choice**: `0001_initial.py` is hand-written. Future revisions MAY use
`--autogenerate` once schema is stable.
**Rationale**: Alembic autogenerate cannot detect `Vector(...)` columns
reliably and never emits `CREATE EXTENSION` / `CREATE INDEX ... USING
hnsw`. Handwriting once is cheaper than fighting the tool.

### ADR-0015: Hybrid ontology layout

**Choice**: Data files at `packages/ontology/{notes.yaml, accords.yaml,
synonyms.json, schema.md}` (no `pyproject.toml`). Loader at
`apps/api/src/fragwise_api/ontology/loader.py`.
**Alternatives**: Promote `packages/ontology/` to a uv-workspace Python
package (premature; flips the workspace toggle the 0b ADR-0006 explicitly
deferred); module under `apps/api` only (violates the brief).
**Rationale**: Data is portable and language-agnostic; loader stays
testable inside the api app; no workspace flip.

### ADR-0016: Embedding row shape

**Choice**: One row per `(fragrance_id, view, model, dimensions)`, with
`view` defaulting to `'combined'`. Per-row `model`, `dimensions`, and
`source_hash`. UNIQUE constraint covers all four columns.
**Rationale**: Ships single-view today (`combined`) but the `view` column
makes the multi-view future a pure data migration. `model`+`dimensions`
support partial backfills when bumping models. `source_hash` is the
idempotency key.

### ADR-0017: Concentration as lookup table

**Choice**: `concentrations(id, slug, name)` lookup. Migration seeds 5
rows: `edp`, `edt`, `cologne`, `parfum`, `extrait`.
**Alternatives**: PG ENUM.
**Rationale**: Contributors can add a concentration via PR with no
migration. Trade-off: a JOIN per fragrance, acceptable.

### ADR-0018: ENUM on `gender` and `fragrance_note_role`

**Choice**: Native PG ENUMs `fragrance_gender` (`masc`, `fem`, `unisex`,
`genderfree`) and `fragrance_note_role` (`top`, `heart`, `base`).
**Rationale**: Tiny, closed sets. PG16 supports `ALTER TYPE ... ADD
VALUE IF NOT EXISTS`, so future evolution is non-blocking.

## Data Flow

```
Migration  (alembic upgrade head)
  └─→ CREATE EXTENSION vector
  └─→ CREATE TYPE fragrance_gender, fragrance_note_role
  └─→ CREATE TABLE brands, perfumers, concentrations, notes,
                   accords, articles, fragrances,
                   fragrance_notes, fragrance_perfumers,
                   fragrance_articles, fragrance_embeddings
  └─→ CREATE INDEX (B-tree on slugs/FKs, GIN FTS, HNSW on embedding)
  └─→ INSERT INTO concentrations (5 rows)

ingest_ontology.py  ──reads──→ packages/ontology/{notes,accords}.yaml
                    ──upserts→ notes, accords  (idempotent on slug)

seed_minimal_fragrances.py  ──reads──→ data/seed/minimal_fragrances.yaml
                            ──upserts→ brands, perfumers, fragrances,
                                       fragrance_notes,
                                       fragrance_perfumers
                            (source_hash per fragrance)

embed_fragrances.py  ──reads──→ fragrances + existing embeddings
                     ──skips──→ rows where source_hash matches
                     ──calls──→ OpenAI embeddings.create(
                                  model='text-embedding-3-small',
                                  input=batch[:100], dimensions=512)
                     ──upserts→ fragrance_embeddings

FastAPI lifespan
  └─→ create_async_engine(DATABASE_URL)
  └─→ async_sessionmaker(engine)
  └─→ app.state.{db_engine, db_sessionmaker}
       │
       ├─→ /readyz  ──SELECT 1──→ 200 ok | 503 unready
       └─→ shutdown ──engine.dispose()
```

## File Changes

| File | Action | Description |
|---|---|---|
| `apps/api/pyproject.toml` | Modify | Add 9 runtime + 2 dev deps; add `[tool.pytest.ini_options].markers` and `addopts`. |
| `apps/api/src/fragwise_api/main.py` | Modify | Wire lifespan to engine; add `/readyz`. |
| `apps/api/src/fragwise_api/db/__init__.py` | Create | Empty package marker. |
| `apps/api/src/fragwise_api/db/base.py` | Create | `Base = (AsyncAttrs, DeclarativeBase)`, `UUIDMixin`, `TimestampMixin`. |
| `apps/api/src/fragwise_api/db/session.py` | Create | `create_async_engine`, `async_sessionmaker`, `get_session` FastAPI dep. |
| `apps/api/src/fragwise_api/db/enums.py` | Create | `Gender`, `NoteRole` Python enums. |
| `apps/api/src/fragwise_api/db/models/__init__.py` | Create | Re-export all models. |
| `apps/api/src/fragwise_api/db/models/{brand,perfumer,concentration,note,accord,article,fragrance}.py` | Create | One model per file. |
| `apps/api/src/fragwise_api/db/models/joins.py` | Create | `FragranceNote`, `FragrancePerfumer`, `FragranceArticle`. |
| `apps/api/src/fragwise_api/db/models/embedding.py` | Create | `FragranceEmbedding` with `vector(512)`. |
| `apps/api/alembic.ini` | Create | Async-friendly config. |
| `apps/api/alembic/env.py` | Create | Async env (Context7 canonical). |
| `apps/api/alembic/script.py.mako` | Create | Default Alembic mako. |
| `apps/api/alembic/versions/0001_initial.py` | Create | Hand-written; tables + indexes + extension + seed. |
| `apps/api/src/fragwise_api/ontology/__init__.py` | Create | Empty. |
| `apps/api/src/fragwise_api/ontology/loader.py` | Create | Pydantic v2 records + 3 loaders. |
| `packages/ontology/notes.yaml` | Create | `version: 1`, ~5 top + ~20 leaf notes. |
| `packages/ontology/accords.yaml` | Create | `version: 1`, 6 families. |
| `packages/ontology/synonyms.json` | Create | `version: 1`, ~30 entries. |
| `packages/ontology/schema.md` | Create | YAML/JSON shape docs. |
| `data/scripts/__init__.py` | Create | Empty marker. |
| `data/scripts/README.md` | Create | Operator order; CI exclusion note. |
| `data/scripts/ingest_ontology.py` | Create | Idempotent upsert. |
| `data/scripts/seed_minimal_fragrances.py` | Create | ~10 fragrances, idempotent. |
| `data/scripts/embed_fragrances.py` | Create | Tenacity retries; batch 100. |
| `data/seed/minimal_fragrances.yaml` | Create | ~10 fragrances input. |
| `apps/api/tests/integration/__init__.py` | Create | Empty. |
| `apps/api/tests/integration/conftest.py` | Create | Testcontainers fixture. |
| `apps/api/tests/integration/test_migrations.py` | Create | Apply + rollback assertions. |
| `apps/api/tests/integration/test_db_session.py` | Create | `SELECT 1` via session. |
| `apps/api/tests/integration/test_ontology_loader.py` | Create | Loader happy + error paths. |
| `apps/api/tests/integration/test_readyz.py` | Create | 200 + 503 cases. |
| `justfile` | Modify | Add 6 recipes. |
| `docker-compose.yml` | Already correct | (`POSTGRES_DB=fragwise` already present — verified.) |

## Cross-cutting Conventions

### UUID v7 generator

```python
# apps/api/src/fragwise_api/db/base.py
import uuid
import uuid_utils
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


def _uuid7() -> uuid.UUID:
    """Stdlib-compatible UUID v7. Cast Rust object to native uuid.UUID."""
    return uuid.UUID(str(uuid_utils.uuid7()))


class Base(AsyncAttrs, DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid7,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

### `source_hash` algorithm (shared by seed + embed)

```python
import hashlib

def compute_source_hash(name: str, description: str | None, notes_csv: str) -> str:
    """SHA-256 of `name|description|notes_csv`. Both seed_minimal_fragrances.py
    and embed_fragrances.py MUST call this same helper."""
    payload = f"{name}|{description or ''}|{notes_csv}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

`notes_csv` is the alphabetized comma-joined slugs of all associated
notes (e.g., `bergamot,jasmine,oakmoss`). Helper lives in
`apps/api/src/fragwise_api/db/__init__.py` so both scripts and tests can
import it via `from fragwise_api.db import compute_source_hash`.

### `DATABASE_URL` contract

App and Alembic both expect a `postgresql+asyncpg://...` URL. If the
operator-supplied URL is `postgresql://...` (sync form), the app's
`db/session.py` performs a one-line normalization at startup so the
example in `.env.example` (`postgresql://user:password@host/dbname`)
still works.

```python
# db/session.py
def _normalize(url: str) -> str:
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url
```

### Operational notes

- Alembic upgrade/downgrade runs are **manual** in dev (`just db-migrate`,
  `just db-rollback`). CI does not invoke alembic — the migration test
  drives it inside pytest via testcontainers.
- `embed_fragrances.py` REQUIRES `OPENAI_API_KEY` and MUST exit non-zero
  if missing. CI MUST NOT call it.
- `ingest_ontology.py` and `seed_minimal_fragrances.py` are safe to
  re-run on dev DBs (idempotent on slug + `source_hash`).

## Interfaces / Contracts

### `db/session.py` (full)

```python
"""Async SQLAlchemy engine + sessionmaker + FastAPI dependency."""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _normalize(url: str) -> str:
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def make_engine(url: str | None = None) -> AsyncEngine:
    raw = url if url is not None else os.environ.get("DATABASE_URL")
    if not raw:
        raise RuntimeError(
            "DATABASE_URL is required. Set it in your environment or .env."
        )
    return create_async_engine(_normalize(raw), pool_pre_ping=True)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(  # FastAPI dep
    request: "fastapi.Request",  # noqa: F821
) -> AsyncIterator[AsyncSession]:
    sm: async_sessionmaker[AsyncSession] = request.app.state.db_sessionmaker
    async with sm() as session:
        yield session
```

### `main.py` (full revised)

```python
"""FastAPI app factory + lifespan + /healthz + /readyz."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from sqlalchemy import text

from fragwise_api.db.session import make_engine, make_sessionmaker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = make_engine()
    app.state.db_engine = engine
    app.state.db_sessionmaker = make_sessionmaker(engine)
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Fragwise API", version="0.0.0", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, Any]:
        from fastapi import Response
        sm = app.state.db_sessionmaker
        try:
            async with sm() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception as exc:  # noqa: BLE001
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={"status": "unready", "error": str(exc)[:200]},
            )

    return app


app = create_app()
```

### Models — `db/models/fragrance.py` (full, representative)

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fragwise_api.db.base import Base, TimestampMixin, UUIDMixin
from fragwise_api.db.enums import Gender

if TYPE_CHECKING:
    from .brand import Brand
    from .concentration import Concentration

gender_enum = ENUM(
    Gender,
    name="fragrance_gender",
    create_type=False,  # created in 0001_initial; see ADR-0018
    values_callable=lambda e: [m.value for m in e],
)


class Fragrance(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "fragrances"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False
    )
    year_released: Mapped[int | None] = mapped_column(nullable=True)
    year_text: Mapped[str | None] = mapped_column(String, nullable=True)
    gender: Mapped[Gender] = mapped_column(gender_enum, nullable=False)
    concentration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concentrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    brand: Mapped["Brand"] = relationship(back_populates="fragrances")
    concentration: Mapped["Concentration | None"] = relationship()

    __table_args__ = (
        Index("ix_fragrances_brand_id", "brand_id"),
        Index("ix_fragrances_slug", "slug"),
    )
```

Other entity models (`brand.py`, `perfumer.py`, `note.py`, `accord.py`,
`article.py`, `concentration.py`) follow the same shape: `(UUIDMixin,
TimestampMixin, Base)`, `slug TEXT UNIQUE NOT NULL`, `name TEXT NOT
NULL`, plus model-specific columns (e.g., `notes.parent_id` self-FK;
`articles.url`, `articles.published_at`, `articles.topics ARRAY(Text)`).

### `db/models/joins.py`

```python
from __future__ import annotations

import uuid
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from fragwise_api.db.base import Base, UUIDMixin
from fragwise_api.db.enums import NoteRole

note_role_enum = ENUM(
    NoteRole, name="fragrance_note_role", create_type=False,
    values_callable=lambda e: [m.value for m in e],
)


class FragranceNote(UUIDMixin, Base):
    __tablename__ = "fragrance_notes"
    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fragrances.id", ondelete="CASCADE"), nullable=False
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[NoteRole] = mapped_column(note_role_enum, nullable=False)
    position: Mapped[int | None] = mapped_column(nullable=True)
    __table_args__ = (
        UniqueConstraint("fragrance_id", "note_id", "role",
                         name="uq_fragrance_notes_fid_nid_role"),
    )


class FragrancePerfumer(UUIDMixin, Base):
    __tablename__ = "fragrance_perfumers"
    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fragrances.id", ondelete="CASCADE"), nullable=False
    )
    perfumer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("perfumers.id", ondelete="RESTRICT"), nullable=False
    )
    __table_args__ = (
        UniqueConstraint("fragrance_id", "perfumer_id",
                         name="uq_fragrance_perfumers_fid_pid"),
    )


class FragranceArticle(UUIDMixin, Base):
    __tablename__ = "fragrance_articles"
    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fragrances.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    __table_args__ = (
        UniqueConstraint("fragrance_id", "article_id",
                         name="uq_fragrance_articles_fid_aid"),
    )
```

### `db/models/embedding.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from fragwise_api.db.base import Base, UUIDMixin


class FragranceEmbedding(UUIDMixin, Base):
    __tablename__ = "fragrance_embeddings"
    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fragrances.id", ondelete="CASCADE"),
        nullable=False,
    )
    view: Mapped[str] = mapped_column(String, nullable=False, server_default="combined")
    embedding: Mapped[list[float]] = mapped_column(Vector(512), nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    dimensions: Mapped[int] = mapped_column(nullable=False)
    source_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        UniqueConstraint(
            "fragrance_id", "view", "model", "dimensions",
            name="uq_fragrance_embeddings_fid_view_model_dim",
        ),
    )
```

### `db/enums.py`

```python
import enum

class Gender(str, enum.Enum):
    masc = "masc"
    fem = "fem"
    unisex = "unisex"
    genderfree = "genderfree"


class NoteRole(str, enum.Enum):
    top = "top"
    heart = "heart"
    base = "base"
```

### `db/models/__init__.py`

```python
from .accord import Accord
from .article import Article
from .brand import Brand
from .concentration import Concentration
from .embedding import FragranceEmbedding
from .fragrance import Fragrance
from .joins import FragranceArticle, FragranceNote, FragrancePerfumer
from .note import Note
from .perfumer import Perfumer

__all__ = [
    "Accord", "Article", "Brand", "Concentration",
    "FragranceArticle", "FragranceEmbedding", "FragranceNote",
    "FragrancePerfumer", "Fragrance", "Note", "Perfumer",
]
```

### `alembic.ini` (full)

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = driver://user:pass@host/dbname

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

The literal `sqlalchemy.url` is a placeholder — `env.py` overrides it
from `DATABASE_URL` at runtime so it never reads the ini value.

### `alembic/env.py` (full)

```python
"""Async Alembic env. Reads DATABASE_URL from environment."""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from fragwise_api.db.base import Base
from fragwise_api.db.models import *  # noqa: F401,F403  -- side-effect import

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _normalize(url: str) -> str:
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _resolved_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for alembic")
    return _normalize(url)


def run_migrations_offline() -> None:
    context.configure(
        url=_resolved_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section, {}) or {}
    section["sqlalchemy.url"] = _resolved_url()
    connectable = async_engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### `alembic/versions/0001_initial.py` (full)

```python
"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

GENDER_VALUES = ("masc", "fem", "unisex", "genderfree")
NOTE_ROLE_VALUES = ("top", "heart", "base")


def upgrade() -> None:
    # 1. Extension owned by the migration.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. ENUM types (must precede tables that reference them).
    gender = postgresql.ENUM(*GENDER_VALUES, name="fragrance_gender", create_type=False)
    note_role = postgresql.ENUM(*NOTE_ROLE_VALUES, name="fragrance_note_role", create_type=False)
    gender.create(op.get_bind(), checkfirst=True)
    note_role.create(op.get_bind(), checkfirst=True)

    # 3. Lookup tables first (FK targets).
    op.create_table(
        "concentrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_concentrations_slug", "concentrations", ["slug"], unique=True)

    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_brands_slug", "brands", ["slug"], unique=True)

    op.create_table(
        "perfumers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_perfumers_slug", "perfumers", ["slug"], unique=True)

    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("notes.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notes_slug", "notes", ["slug"], unique=True)
    op.create_index("ix_notes_parent_id", "notes", ["parent_id"])

    op.create_table(
        "accords",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_accords_slug", "accords", ["slug"], unique=True)

    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("url", sa.String, nullable=True),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("topics", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_articles_slug", "articles", ["slug"], unique=True)

    # 4. Fragrances (depends on brands, concentrations, gender enum).
    op.create_table(
        "fragrances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("year_released", sa.Integer, nullable=True),
        sa.Column("year_text", sa.String, nullable=True),
        sa.Column("gender",
                  postgresql.ENUM(name="fragrance_gender", create_type=False),
                  nullable=False),
        sa.Column("concentration_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("concentrations.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fragrances_slug", "fragrances", ["slug"], unique=True)
    op.create_index("ix_fragrances_brand_id", "fragrances", ["brand_id"])
    op.execute(
        "CREATE INDEX ix_fragrances_fts ON fragrances "
        "USING GIN (to_tsvector('english', name || ' ' || coalesce(description, '')))"
    )

    # 5. M:M joins.
    op.create_table(
        "fragrance_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fragrance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fragrances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("notes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("role",
                  postgresql.ENUM(name="fragrance_note_role", create_type=False),
                  nullable=False),
        sa.Column("position", sa.Integer, nullable=True),
        sa.UniqueConstraint("fragrance_id", "note_id", "role",
                            name="uq_fragrance_notes_fid_nid_role"),
    )
    op.create_index("ix_fragrance_notes_fragrance_id", "fragrance_notes", ["fragrance_id"])
    op.create_index("ix_fragrance_notes_note_id", "fragrance_notes", ["note_id"])

    op.create_table(
        "fragrance_perfumers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fragrance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fragrances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("perfumer_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("perfumers.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("fragrance_id", "perfumer_id",
                            name="uq_fragrance_perfumers_fid_pid"),
    )

    op.create_table(
        "fragrance_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fragrance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fragrances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("article_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("fragrance_id", "article_id",
                            name="uq_fragrance_articles_fid_aid"),
    )

    # 6. Embeddings.
    op.create_table(
        "fragrance_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fragrance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fragrances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("view", sa.String, nullable=False, server_default="combined"),
        sa.Column("embedding", Vector(512), nullable=False),
        sa.Column("model", sa.String, nullable=False),
        sa.Column("dimensions", sa.Integer, nullable=False),
        sa.Column("source_hash", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("fragrance_id", "view", "model", "dimensions",
                            name="uq_fragrance_embeddings_fid_view_model_dim"),
    )
    op.create_index(
        "ix_fragrance_embeddings_hnsw",
        "fragrance_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # 7. Seed concentrations lookup (5 rows).
    op.execute(
        "INSERT INTO concentrations (id, slug, name) VALUES "
        "(gen_random_uuid(), 'edp', 'Eau de Parfum'),"
        "(gen_random_uuid(), 'edt', 'Eau de Toilette'),"
        "(gen_random_uuid(), 'cologne', 'Eau de Cologne'),"
        "(gen_random_uuid(), 'parfum', 'Parfum'),"
        "(gen_random_uuid(), 'extrait', 'Extrait de Parfum')"
    )


def downgrade() -> None:
    op.drop_index("ix_fragrance_embeddings_hnsw", table_name="fragrance_embeddings")
    op.drop_table("fragrance_embeddings")
    op.drop_table("fragrance_articles")
    op.drop_table("fragrance_perfumers")
    op.drop_index("ix_fragrance_notes_note_id", table_name="fragrance_notes")
    op.drop_index("ix_fragrance_notes_fragrance_id", table_name="fragrance_notes")
    op.drop_table("fragrance_notes")
    op.execute("DROP INDEX IF EXISTS ix_fragrances_fts")
    op.drop_index("ix_fragrances_brand_id", table_name="fragrances")
    op.drop_index("ix_fragrances_slug", table_name="fragrances")
    op.drop_table("fragrances")
    op.drop_index("ix_articles_slug", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_accords_slug", table_name="accords")
    op.drop_table("accords")
    op.drop_index("ix_notes_parent_id", table_name="notes")
    op.drop_index("ix_notes_slug", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_perfumers_slug", table_name="perfumers")
    op.drop_table("perfumers")
    op.drop_index("ix_brands_slug", table_name="brands")
    op.drop_table("brands")
    op.drop_index("ix_concentrations_slug", table_name="concentrations")
    op.drop_table("concentrations")
    op.execute("DROP TYPE IF EXISTS fragrance_note_role")
    op.execute("DROP TYPE IF EXISTS fragrance_gender")
    op.execute("DROP EXTENSION IF EXISTS vector")
```

The `gen_random_uuid()` calls in seed are PG-native (provided by
`pgcrypto` or `pg16`'s built-ins). The seed rows are immutable canonical
slugs; `ingest_ontology.py` may upsert additional concentrations later
via Python-generated UUID v7.

### `ontology/loader.py` (full)

```python
"""Pydantic v2 ontology loader."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ONTOLOGY_DIR = Path(__file__).resolve().parents[4] / "packages" / "ontology"


class _BaseDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = Field(..., description="schema version")


class NoteRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    name: str
    parent_slug: str | None = None


class NotesDocument(_BaseDoc):
    notes: list[NoteRecord]


class AccordRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    name: str


class AccordsDocument(_BaseDoc):
    accords: list[AccordRecord]


class SynonymRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical: str
    synonyms: list[str]


class SynonymsDocument(_BaseDoc):
    synonyms: list[SynonymRecord]


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"ontology file not found: {path}")
    return yaml.safe_load(path.read_text())


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"ontology file not found: {path}")
    return json.loads(path.read_text())


def _validate(model: type[BaseModel], raw: dict, path: Path) -> BaseModel:
    if not isinstance(raw, dict) or "version" not in raw:
        raise ValueError(f"missing top-level 'version' field in {path}")
    try:
        return model.model_validate(raw)
    except ValidationError as e:
        raise ValueError(f"invalid ontology document at {path}: {e}") from e


def load_notes(directory: Path | None = None) -> list[NoteRecord]:
    p = (directory or ONTOLOGY_DIR) / "notes.yaml"
    doc = _validate(NotesDocument, _read_yaml(p), p)
    return doc.notes  # type: ignore[attr-defined]


def load_accords(directory: Path | None = None) -> list[AccordRecord]:
    p = (directory or ONTOLOGY_DIR) / "accords.yaml"
    doc = _validate(AccordsDocument, _read_yaml(p), p)
    return doc.accords  # type: ignore[attr-defined]


def load_synonyms(directory: Path | None = None) -> list[SynonymRecord]:
    p = (directory or ONTOLOGY_DIR) / "synonyms.json"
    doc = _validate(SynonymsDocument, _read_json(p), p)
    return doc.synonyms  # type: ignore[attr-defined]
```

`ONTOLOGY_DIR` is computed relative to the loader file: `apps/api/src/
fragwise_api/ontology/loader.py` → `../../../../packages/ontology`.
The `directory=` kwarg keeps tests injectable.

### `packages/ontology/notes.yaml` (full)

```yaml
# EXAMPLES — replace with curated data in a follow-up phase.
version: 1
notes:
  # Top-level (parent_slug: null)
  - slug: citrus
    name: Citrus
  - slug: woody
    name: Woody
  - slug: floral
    name: Floral
  - slug: gourmand
    name: Gourmand
  - slug: aquatic
    name: Aquatic

  # Citrus children
  - { slug: bergamot,    name: Bergamot,    parent_slug: citrus }
  - { slug: lemon,       name: Lemon,       parent_slug: citrus }
  - { slug: orange,      name: Orange,      parent_slug: citrus }
  - { slug: grapefruit,  name: Grapefruit,  parent_slug: citrus }

  # Woody children
  - { slug: sandalwood,  name: Sandalwood,  parent_slug: woody }
  - { slug: cedarwood,   name: Cedarwood,   parent_slug: woody }
  - { slug: vetiver,     name: Vetiver,     parent_slug: woody }
  - { slug: oud,         name: Oud,         parent_slug: woody }

  # Floral children
  - { slug: rose,        name: Rose,        parent_slug: floral }
  - { slug: jasmine,     name: Jasmine,     parent_slug: floral }
  - { slug: tuberose,    name: Tuberose,    parent_slug: floral }
  - { slug: iris,        name: Iris,        parent_slug: floral }

  # Gourmand children
  - { slug: vanilla,     name: Vanilla,     parent_slug: gourmand }
  - { slug: tonka,       name: Tonka Bean,  parent_slug: gourmand }
  - { slug: caramel,     name: Caramel,     parent_slug: gourmand }

  # Aquatic children
  - { slug: salt,        name: Sea Salt,    parent_slug: aquatic }
  - { slug: ozonic,      name: Ozonic,      parent_slug: aquatic }
```

### `packages/ontology/accords.yaml` (full)

```yaml
# EXAMPLES — replace with curated data in a follow-up phase.
version: 1
accords:
  - { slug: chypre,    name: Chypre }
  - { slug: fougere,   name: Fougere }
  - { slug: oriental,  name: Oriental }
  - { slug: gourmand,  name: Gourmand }
  - { slug: aquatic,   name: Aquatic }
  - { slug: woody,     name: Woody }
```

### `packages/ontology/synonyms.json` (full skeleton)

```json
{
  "version": 1,
  "synonyms": [
    {"canonical": "bergamot",   "synonyms": ["bergamotto", "citrus bergamia"]},
    {"canonical": "oud",        "synonyms": ["agarwood", "oudh"]},
    {"canonical": "vetiver",    "synonyms": ["khus"]},
    {"canonical": "sandalwood", "synonyms": ["santal", "santalum album"]},
    {"canonical": "vanilla",    "synonyms": ["vanille"]}
  ]
}
```

(Final file ships ~30 entries; the skeleton above is illustrative — the
implementer fills it out from a curated public domain list.)

### `packages/ontology/schema.md` (full)

```markdown
# Ontology File Schema (v1)

All three files MUST declare a top-level `version: 1`. The loader rejects
files without `version` and files declaring an unknown version.

## notes.yaml
```yaml
version: 1
notes:
  - { slug: <kebab>, name: <display>, parent_slug: <kebab|null> }
```
Slugs MUST be unique. `parent_slug` MAY reference any other slug in the
same file. Tree depth is 1 (top-level + leaf) for v1.

## accords.yaml
```yaml
version: 1
accords:
  - { slug: <kebab>, name: <display> }
```
Slugs MUST be unique.

## synonyms.json
```json
{ "version": 1,
  "synonyms": [
    { "canonical": "<slug>", "synonyms": ["<text>", ...] }
  ] }
```
`canonical` SHOULD reference an existing note or accord slug. Search
uses synonyms to expand user queries.

## Validation
The loader validates with pydantic v2 (`extra=forbid`). Unknown fields
fail loudly. Missing `version` fails loudly. Loader is idempotent and
free of side effects — DB writes happen in `ingest_ontology.py`.
```

### Ingestion script skeletons

```python
# data/scripts/ingest_ontology.py
"""Idempotent UPSERT of notes + accords."""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from fragwise_api.db.models import Accord, Note
from fragwise_api.db.session import make_engine, make_sessionmaker
from fragwise_api.ontology.loader import load_accords, load_notes


async def _upsert_accords(session) -> None:
    rows = [{"id": _uuid7(), "slug": a.slug, "name": a.name} for a in load_accords()]
    stmt = pg_insert(Accord.__table__).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["slug"], set_={"name": stmt.excluded.name}
    )
    await session.execute(stmt)


async def _upsert_notes(session) -> None:
    records = load_notes()
    # Two passes so parent_id resolves.
    base = [{"id": _uuid7(), "slug": n.slug, "name": n.name, "parent_id": None}
            for n in records]
    stmt = pg_insert(Note.__table__).values(base)
    stmt = stmt.on_conflict_do_update(
        index_elements=["slug"], set_={"name": stmt.excluded.name}
    )
    await session.execute(stmt)
    # Now backfill parent_id for child notes.
    slug_to_id = {row.slug: row.id for row in (
        await session.execute(select(Note.slug, Note.id))).all()}
    for n in records:
        if n.parent_slug:
            await session.execute(
                Note.__table__.update()
                    .where(Note.slug == n.slug)
                    .values(parent_id=slug_to_id[n.parent_slug])
            )


async def main() -> None:
    engine = make_engine()
    sm = make_sessionmaker(engine)
    async with sm() as session:
        await _upsert_accords(session)
        await _upsert_notes(session)
        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
```

`_uuid7()` imports from `fragwise_api.db.base`. Path bootstrap: scripts
run as `cd apps/api && uv run python ../../data/scripts/ingest_ontology.py`
(or via `just ingest`); the `apps/api/.venv` resolves `fragwise_api`.

```python
# data/scripts/seed_minimal_fragrances.py
"""Idempotent seed of ~10 example fragrances."""
from __future__ import annotations

import asyncio
from pathlib import Path

import yaml
from python_slugify import slugify
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from fragwise_api.db import compute_source_hash
from fragwise_api.db.base import _uuid7
from fragwise_api.db.enums import Gender, NoteRole
from fragwise_api.db.models import (
    Brand, Fragrance, FragranceNote, FragrancePerfumer, Note, Perfumer,
)
from fragwise_api.db.session import make_engine, make_sessionmaker

SEED_PATH = Path(__file__).resolve().parents[1] / "seed" / "minimal_fragrances.yaml"


async def main() -> None:
    engine = make_engine()
    sm = make_sessionmaker(engine)
    raw = yaml.safe_load(SEED_PATH.read_text())
    async with sm() as session:
        # ... upsert brands, perfumers, fragrances, fragrance_notes,
        #     fragrance_perfumers, all keyed on slug.
        # ... compute source_hash per fragrance and store on a side
        #     column? In 0c we keep source_hash only on embeddings;
        #     the seed script stores the hash in a local sidecar so
        #     embed_fragrances.py can compare.
        ...
        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
```

The implementer fills in the upsert bodies following the same
`pg_insert(...).on_conflict_do_update(...)` pattern as
`ingest_ontology.py`. `data/seed/minimal_fragrances.yaml` is the input —
each entry has `name`, `brand`, `perfumers`, `concentration`, `gender`,
`year_released`, `notes` (`top`, `heart`, `base` lists of slugs),
`description`.

```python
# data/scripts/embed_fragrances.py
"""Embed fragrances. Idempotent on source_hash. Tenacity-retried."""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Iterable

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from tenacity import (
    AsyncRetrying, stop_after_attempt, wait_exponential, retry_if_exception_type,
)

from fragwise_api.db import compute_source_hash
from fragwise_api.db.base import _uuid7
from fragwise_api.db.models import Fragrance, FragranceEmbedding, Note, FragranceNote
from fragwise_api.db.session import make_engine, make_sessionmaker

MODEL = "text-embedding-3-small"
DIMENSIONS = 512
BATCH = 100


def _build_canonical_text(name, brand_name, concentration, notes_csv, description):
    return f"{brand_name} {name} ({concentration or 'unknown'}). " \
           f"Notes: {notes_csv}. {description or ''}".strip()


async def _embed_batch(client: AsyncOpenAI, inputs: list[str]) -> list[list[float]]:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    ):
        with attempt:
            resp = await client.embeddings.create(
                model=MODEL, input=inputs, dimensions=DIMENSIONS,
            )
            return [d.embedding for d in resp.data]
    raise RuntimeError("unreachable")


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is required to run embed_fragrances.py",
              file=sys.stderr)
        sys.exit(2)
    client = AsyncOpenAI()
    engine = make_engine()
    sm = make_sessionmaker(engine)
    async with sm() as session:
        # 1. Load fragrances joined to existing embeddings; compute
        #    canonical text per fragrance; compute source_hash; skip
        #    rows where the existing row's source_hash matches.
        # 2. Batch up to 100, call _embed_batch, upsert into
        #    fragrance_embeddings keyed on (fragrance_id, view='combined',
        #    model, dimensions).
        ...
        await session.commit()
    await engine.dispose()
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### `data/scripts/README.md`

```markdown
# Operator scripts

Run order against a freshly migrated database:

    just db-migrate   # alembic upgrade head
    just ingest       # python data/scripts/ingest_ontology.py
    just seed         # python data/scripts/seed_minimal_fragrances.py
    just embed        # python data/scripts/embed_fragrances.py  (needs OPENAI_API_KEY)

All scripts are idempotent and safe to re-run.

These scripts are NEVER invoked from CI. CI runs only the test suite,
which uses testcontainers for DB tests and stubs the OpenAI embedder.
```

### Tests

```python
# apps/api/tests/integration/conftest.py
"""Integration test fixtures: pgvector testcontainer."""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

PGVECTOR_IMAGE = "pgvector/pgvector:pg16"


@pytest.fixture(scope="session")
def pg_container() -> "PostgresContainer":
    with PostgresContainer(
        image=PGVECTOR_IMAGE, driver="asyncpg", username="fragwise",
        password="fragwise", dbname="fragwise",
    ) as pg:
        yield pg


@pytest.fixture(scope="session")
def database_url(pg_container: PostgresContainer) -> str:
    url = pg_container.get_connection_url()
    os.environ["DATABASE_URL"] = url
    return url


@pytest_asyncio.fixture(scope="session")
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(database_url)
    yield eng
    await eng.dispose()
```

```python
# apps/api/tests/integration/test_migrations.py
"""Apply + rollback the initial migration; assert schema state."""
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

pytestmark = pytest.mark.integration


def _alembic_cfg(database_url: str) -> Config:
    import os
    os.environ["DATABASE_URL"] = database_url
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    return cfg


@pytest.mark.asyncio
async def test_upgrade_creates_tables_and_extension(database_url, engine):
    cfg = _alembic_cfg(database_url)
    command.upgrade(cfg, "head")
    async with engine.connect() as conn:
        tables = (await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        ))).scalars().all()
        for t in ("brands", "perfumers", "concentrations", "notes", "accords",
                  "articles", "fragrances", "fragrance_notes",
                  "fragrance_perfumers", "fragrance_articles",
                  "fragrance_embeddings"):
            assert t in tables, t
        ext = (await conn.execute(text(
            "SELECT extname FROM pg_extension WHERE extname='vector'"
        ))).scalar()
        assert ext == "vector"
        # HNSW index exists
        idx = (await conn.execute(text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename='fragrance_embeddings' "
            "AND indexname='ix_fragrance_embeddings_hnsw'"
        ))).scalar()
        assert idx and "hnsw" in idx and "vector_cosine_ops" in idx


@pytest.mark.asyncio
async def test_downgrade_empties_schema(database_url, engine):
    cfg = _alembic_cfg(database_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    async with engine.connect() as conn:
        tables = (await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        ))).scalars().all()
        for t in ("brands", "fragrances", "fragrance_embeddings"):
            assert t not in tables
        ext = (await conn.execute(text(
            "SELECT extname FROM pg_extension WHERE extname='vector'"
        ))).scalar()
        assert ext is None
```

```python
# apps/api/tests/integration/test_db_session.py
import pytest
from sqlalchemy import text
from fragwise_api.db.session import make_engine, make_sessionmaker

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_select_one(database_url):
    engine = make_engine(database_url)
    sm = make_sessionmaker(engine)
    async with sm() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    await engine.dispose()
```

```python
# apps/api/tests/integration/test_ontology_loader.py
import pytest
from pathlib import Path

from fragwise_api.ontology.loader import (
    load_accords, load_notes, load_synonyms,
)

pytestmark = pytest.mark.integration  # marker is fine here even though no DB


def test_load_notes_happy_path():
    notes = load_notes()
    assert any(n.slug == "bergamot" for n in notes)
    assert any(n.slug == "citrus" and n.parent_slug is None for n in notes)


def test_loader_rejects_missing_version(tmp_path: Path):
    p = tmp_path / "notes.yaml"
    p.write_text("notes: []\n")
    with pytest.raises(Exception, match="version"):
        load_notes(directory=tmp_path)
```

```python
# apps/api/tests/integration/test_readyz.py
"""Both 200 (DB up) and 503 (DB down) cases."""
import os
import pytest
import httpx
from alembic import command
from alembic.config import Config

pytestmark = pytest.mark.integration


def _cfg(url: str) -> Config:
    os.environ["DATABASE_URL"] = url
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    return cfg


@pytest.mark.asyncio
async def test_readyz_up(database_url):
    command.upgrade(_cfg(database_url), "head")
    from fragwise_api.main import create_app
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        async with app.router.lifespan_context(app):
            r = await c.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_readyz_down(monkeypatch):
    monkeypatch.setenv("DATABASE_URL",
        "postgresql+asyncpg://fragwise:fragwise@127.0.0.1:1/none")
    from fragwise_api.main import create_app
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        async with app.router.lifespan_context(app):
            r = await c.get("/readyz")
    assert r.status_code == 503
    assert r.json()["status"] == "unready"
```

### `pyproject.toml` diff

```toml
# Added under [project] dependencies (append to existing list):
"sqlalchemy[asyncio]>=2.0.40,<3.0",
"asyncpg>=0.30,<1.0",
"alembic>=1.14,<2.0",
"pgvector>=0.4,<1.0",
"pydantic>=2.10,<3.0",
"pyyaml>=6.0,<7.0",
"openai>=1.55,<3.0",
"tenacity>=9.0,<10.0",
"uuid-utils>=0.10,<1.0",
"python-slugify>=8.0,<9.0",

# Added under [dependency-groups].dev (append):
"testcontainers[postgres]>=4.9,<5.0",
"types-pyyaml>=6.0,<7.0",

# Replaced [tool.pytest.ini_options]:
[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra --strict-markers -m 'not integration'"
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "integration: requires Docker; opt-in via -m integration",
]
```

### `justfile` recipe additions

```make
# Apply migrations against the dev DB.
db-migrate:
    cd apps/api && uv run alembic upgrade head

# Roll all migrations back.
db-rollback:
    cd apps/api && uv run alembic downgrade base

# Drop and re-apply (dev only).
db-reset:
    cd apps/api && uv run alembic downgrade base
    cd apps/api && uv run alembic upgrade head

# Ingest ontology (notes + accords) idempotently.
ingest:
    cd apps/api && uv run python ../../data/scripts/ingest_ontology.py

# Seed ~10 example fragrances idempotently.
seed:
    cd apps/api && uv run python ../../data/scripts/seed_minimal_fragrances.py

# Embed fragrances using OpenAI. Requires OPENAI_API_KEY.
embed:
    cd apps/api && uv run python ../../data/scripts/embed_fragrances.py

# Run integration tests (requires Docker).
test-integration:
    cd apps/api && uv run pytest -m integration
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Loader rejects malformed/missing-version files; `compute_source_hash` deterministic | pytest, no DB |
| Unit | `_normalize` URL conversion | pytest |
| Integration | Migration upgrade creates tables, ENUMs, extension, HNSW index | testcontainers `pgvector/pgvector:pg16`, marker `integration` |
| Integration | Migration downgrade empties schema (extension dropped, ENUMs dropped) | same fixture |
| Integration | DB session executes `SELECT 1` | `make_engine`/`make_sessionmaker` against testcontainer |
| Integration | Loader returns valid records when ontology files exist | uses repo's actual `packages/ontology/*` |
| Integration | `/readyz` returns 200 against migrated container; 503 against unreachable URL | ASGI transport + lifespan |
| Manual | `just ingest` then `just seed` then `just embed` round-trip on dev DB | operator only; not in CI |

CI (`api.yml`) still runs `pytest` without `-m integration` — no behavior
change required by 0c. Docker is available on `ubuntu-latest` runners; we
will add `-m integration` to the workflow in a follow-up phase if the
integration suite is wanted in CI; 0c keeps CI green and fast.

## Migration / Rollout

- Pre-merge: `git reset` reverts all paths.
- Post-merge, pre-deploy: revert merge commit (no production state).
- Post-deploy: `just db-rollback` runs the initial revision's
  `downgrade()`, dropping every project table, every ENUM, and the
  vector extension.

## Open Questions

None blocking. The proposal closed Q1 (UUID v7), Q4 (year int + nullable
text, gender ENUM, concentration lookup), Q6 (single embedding row +
reserved `view`), and Q24 (`/readyz` ships in 0c). Remaining lean
answers (Q2/Q5/Q7/Q8/Q12/Q15/Q20/Q25) are ratified above.

---

## Return Envelope

**Status**: success
**Executive Summary**: Wrote a paste-ready technical design for
`phase-0c-schema-and-ontology`. Verified pins via Context7 on 2026-05-06
(SQLAlchemy 2.0.40+, Alembic 1.14+, pgvector 0.4+, OpenAI Python 2.x with
`dimensions=512`, testcontainers 4.9+, uuid-utils 0.10+ for v7). Captured
8 ADRs (0011-0018) covering UUID v7 PKs, async Alembic env, hand-written
initial revision, hybrid ontology layout, embedding row shape with
reserved `view` column, concentration as lookup, ENUM on gender/note
role, testcontainers > GH services. Provided full file content for
`base.py`, `session.py`, `main.py` revision, `enums.py`,
`models/__init__.py`, `models/fragrance.py`, `models/joins.py`,
`models/embedding.py`, `alembic.ini`, `alembic/env.py`,
`alembic/versions/0001_initial.py` (CREATE EXTENSION + 11 tables + 5
seeded concentrations + B-tree, GIN/FTS, and HNSW indexes + complete
downgrade), `ontology/loader.py`, `notes.yaml`, `accords.yaml`,
`synonyms.json`, `schema.md`, ingest/seed/embed script skeletons,
`data/scripts/README.md`, integration tests (migrations, db_session,
ontology_loader, readyz), `pyproject.toml` deps + pytest markers, and 6
new `justfile` recipes. Documented `_uuid7` generator, shared
`compute_source_hash` algorithm, `DATABASE_URL` async normalization, and
operational notes (scripts NOT in CI; embed REQUIRES OPENAI_API_KEY).
**Artifacts**:
- `openspec/changes/phase-0c-schema-and-ontology/design.md`
**Next Recommended**: `sdd-tasks phase-0c-schema-and-ontology` to break
the design into an implementation checklist.
**Risks**:
- R1 pgvector autogenerate gap — hand-written initial revision (ADR-0014)
- R2 testcontainers needs Docker — opt-in `integration` marker; CI skips
  by default (revisit when integration suite is desired in CI)
- R3 `OPENAI_API_KEY` MUST NOT run in CI — embed_fragrances.py never
  invoked from CI; tests stub the embedder
- R4 PG seed uses `gen_random_uuid()` for the 5 concentration rows —
  PG16 ships this built-in; if any deployment uses PG <13 we would need
  `pgcrypto` (not a concern given Neon parity at PG16)
- R5 `view` column shipped from day 1 with default `'combined'`; future
  multi-view is a data migration only
- R8 ingest/seed re-run pollution — idempotent UPSERT keyed on slug;
  tests assert row count stable across two runs
- R10 contributors without Docker — `addopts = "-m 'not integration'"`
  default keeps unit tests green; CONTRIBUTING note follows in tasks
- R13 ENUM evolution — PG16 supports `ALTER TYPE ... ADD VALUE IF NOT
  EXISTS`; documented in ADR-0018
