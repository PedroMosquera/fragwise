# Exploration: phase-0c-schema-and-ontology

Investigation of the third and final foundation change: SQLAlchemy 2.0 + asyncpg
DB models, Alembic migrations (incl. pgvector extension and HNSW index),
DB pool wired into the FastAPI lifespan, the `packages/ontology/` skeleton
(notes/accords YAML + synonyms JSON + loader), `data/scripts/` ingestion
skeleton (ontology ingest, minimal seed, OpenAI embeddings), DB integration
tests, justfile and `api.yml` CI extensions, and the cross-cutting widening
of `repo-skeleton`'s permitted-paths rule.

This document only surfaces unknowns, risks, and trade-offs. No code or
design decisions are made — those land in `sdd-propose` and `sdd-design`.

## Current State

- `apps/api` is a working FastAPI scaffold (single uv project, Python 3.12,
  ruff/mypy strict/pytest passing). `pyproject.toml` declares `fastapi`,
  `uvicorn`, `langgraph~=1.0.8`, `httpx`, `python-dotenv`. **No SQLAlchemy,
  no asyncpg, no Alembic, no pydantic, no openai SDK.**
- `apps/api/src/fragwise_api/main.py` exposes `create_app()` with a no-op
  `lifespan(app)` async context manager and a `/healthz` endpoint that
  returns `{"status": "ok"}` without touching anything. The lifespan
  docstring already says: "Empty in 0b; 0c plugs in DB + Redis here."
- `docker-compose.yml` runs `pgvector/pgvector:pg16` (Neon-parity) and
  `redis:7-alpine` with credentials `fragwise/fragwise/fragwise`. Healthcheck
  is `pg_isready`. No init scripts, no `command:` overrides.
- `packages/ontology/` exists but contains only `.gitkeep`. Same for
  `data/seed/` and `data/scripts/`.
- `.env.example` declares `DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require`
  and `OPENAI_API_KEY=...`. Both keys are documented, no real values.
- `justfile` has 14 recipes (install, dev, dev-web, dev-api, test, test-web,
  test-api, lint, lint-web, lint-api, db-up, db-down, db-shell, default).
  No `db-migrate`, `db-rollback`, `db-reset`, `ingest`, or `embed`.
- `.github/workflows/api.yml` runs uv sync, ruff, ruff format check, mypy,
  pytest. No `services:` block, no postgres, no migration step.
- `repo-skeleton` spec (the canonical version after 0b's archive) declares
  permitted paths as `apps/web/**`, `apps/api/**`, repo-root
  `docker-compose.yml` + `justfile`, and `.github/workflows/**`. **No
  `data/scripts/**`, no `packages/ontology/**` content, no
  `apps/api/alembic/**` or `apps/api/migrations/**`.** The 0b design's
  cross-cutting note explicitly punts this widening to 0c.
- Versions verified via Context7 on 2026-05-06: SQLAlchemy 2.0 async +
  asyncpg via `create_async_engine("postgresql+asyncpg://...")`; Alembic
  ships an `init -t async` template and recommends `op.execute()` for
  custom DDL like `CREATE EXTENSION` and `CREATE INDEX ... USING hnsw`;
  pgvector documents HNSW index syntax with `vector_cosine_ops` and
  `WITH (m = 16, ef_construction = 64)` defaults; testcontainers-python
  exposes `PostgresContainer(image=..., driver=...)` with
  `get_connection_url()`; OpenAI Python `client.embeddings.create(model,
  input, dimensions)` supports list inputs and dimension reduction on the
  `text-embedding-3-*` family.

## Affected Areas

Pure additions plus three small modifications. Footprint:

- **`apps/api/pyproject.toml`** — Modify. Add runtime deps `sqlalchemy[asyncio]`,
  `asyncpg`, `alembic`, `pgvector` (Python bindings for SQLAlchemy types),
  `pydantic`, `openai`, `pyyaml`, `tenacity` (retry/backoff for embed script).
  Add dev deps `testcontainers[postgresql]`, `pytest-postgresql` (alternative
  to testcontainers — see Q11), `types-pyyaml`.
- **`apps/api/src/fragwise_api/db/`** — New package. Layout TBD by design
  (recommended in this exploration: `models.py`, `session.py`, `__init__.py`).
- **`apps/api/src/fragwise_api/main.py`** — Modify lifespan to construct an
  `AsyncEngine` + `async_sessionmaker`, store on `app.state`, dispose on
  shutdown. Possibly add `/readyz` (pings DB) — out of strict scope but
  the 0b design said `/readyz` lands in 0c.
- **`apps/api/alembic/`** — New. `env.py`, `script.py.mako`, `versions/<rev>_initial.py`.
- **`apps/api/alembic.ini`** — New.
- **`packages/ontology/`** — New content. `notes.yaml`, `accords.yaml`,
  `synonyms.json`, `schema.md`, `loader.py`, possibly `pyproject.toml` if it
  becomes a sibling Python package (see Q5).
- **`data/scripts/`** — New. `ingest_ontology.py`, `seed_minimal_fragrances.py`,
  `embed_fragrances.py`, plus a small `__init__.py`/README.
- **`data/seed/`** — New `minimal_fragrances.yaml` (or .json) — the ~10
  example fragrances input file consumed by `seed_minimal_fragrances.py`.
- **`apps/api/tests/`** — New `test_migrations.py`, `test_ontology_loader.py`,
  `test_db_session.py`. Possibly extend `conftest.py` with a postgres
  container fixture.
- **`docker-compose.yml`** — Possibly modify to add an `init` script mounting
  `CREATE EXTENSION vector` (probably unnecessary — the pgvector image runs
  it on first init already; verify).
- **`justfile`** — Add `db-migrate`, `db-rollback`, `db-reset`, `ingest`,
  `embed` (and possibly `seed`).
- **`.github/workflows/api.yml`** — Add `services.postgres` block (or step
  that boots compose), add "alembic upgrade head" step, ensure DB tests run.
- **`openspec/specs/repo-skeleton/`** — Modify spec via delta to widen the
  permitted-paths list to include `data/scripts/**`, `packages/ontology/**`
  content, and `apps/api/alembic/**`.
- **`openspec/specs/api-app/`** — Modify spec via delta. New requirements:
  DB session in lifespan, Alembic present, ontology loader, ingest scripts,
  embedding script. Possibly a new spec capability `db-schema` or
  `ontology` if those feel separable enough.
- **`openspec/specs/dev-infra/`** — Possibly modify if compose changes (else
  no delta needed).
- **`openspec/specs/ci-pipeline/`** — Modify spec via delta. New requirement:
  api workflow runs migrations against postgres service container.
- **`openspec/config.yaml`** — Probably no changes (context already names
  pgvector).

## Key Unknowns (decisions for sdd-propose)

### Q1. Identifier strategy: `BIGSERIAL` int PK vs `UUID` PK

| Choice | Pros | Cons |
|---|---|---|
| `BIGSERIAL` int PK | Faster joins, smaller indexes, friendlier in URLs (`/fragrances/12345`), psql-friendly | Forks/merges across deployments collide (e.g., contributor A's id=42 and contributor B's id=42 are different fragrances) |
| `UUID v7` (time-sortable) PK | Distributed-friendly, fork-safe, mergeable seed dumps, good index locality | Larger storage (16 bytes vs 8), uglier URLs unless `slug` is the canonical public id, every join is wider |
| Hybrid (int PK + UUID natural key) | Best of both | Two unique columns per table, more code |

**Lean**: UUID v7 PK on **content tables** (`fragrances`, `brands`, `perfumers`,
`articles`, `fragrance_embeddings`) because OSS forks will dump-and-merge
seed data; `BIGSERIAL` on **lookup tables** (`notes`, `accords`,
`fragrance_notes`, `fragrance_perfumers`) because they're internal join
fodder and never publicly addressed. PostgreSQL 18 has native `uuidv7()` but
PG16 does not; would need either an extension (`pg_uuidv7`) or generation
in Python via `uuid_utils` / hand-rolled. Decide before sdd-propose.

### Q2. Slug strategy

- Auto-generate from `name` (slugify lowercase, dash-separated) on insert?
- Manual `slug` column required at insert time (caller computes)?
- Composite slug for fragrances (e.g., `<brand-slug>/<fragrance-slug>`) since
  many fragrances share names across brands ("Mon Guerlain" vs "Mon Numero
  10")?

Lean: store `slug` as a non-null unique column, generated by the seed/ingest
script using `python-slugify`, scoped per-brand for fragrances (`UNIQUE
(brand_id, slug)`) and globally unique for `brands`/`perfumers`.

### Q3. Timestamps and soft delete

- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` on every table — yes/no?
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` with a trigger or app-side
  hook? SQLAlchemy `onupdate=func.now()` covers app-side writes; a Postgres
  trigger covers raw-SQL writes from scripts.
- Soft delete via `deleted_at TIMESTAMPTZ NULL` vs hard delete?

Lean: `created_at` + `updated_at` on every content table (fragrances, brands,
perfumers, articles); skip on join tables (`fragrance_notes`,
`fragrance_perfumers`) — they're rebuilt on ingest. **No** soft delete in v1
— Fragwise is a public catalog, not a CRM; if a fragrance is removed it's
because it doesn't belong, hard delete is correct. Use SQLAlchemy
`onupdate=func.now()` rather than a DB trigger to keep the migration
simple.

### Q4. Loose-typed columns: `year_released`, `gender`, `concentration`

- **`year_released`**: vintage fragrances often have unknown exact dates.
  Options: `INTEGER NULL` (year only, e.g., 1921), `DATE NULL` (over-precise
  for a year), or `TEXT NULL` (free text like "circa 1920s"). Lean: **INTEGER
  with CHECK (year_released BETWEEN 1700 AND 2100)** plus a separate
  `year_released_text TEXT NULL` for "circa 1920s" / "unknown" cases. Costs
  one extra nullable column; simple.
- **`gender`**: domain values are masc / fem / unisex / genderfree. Closed set
  ⇒ Postgres `ENUM` or a `gender` lookup table. Lean: native `ENUM` —
  Alembic supports it via `sa.Enum(... name="fragrance_gender")`. ENUM evolution
  needs care (`ALTER TYPE ... ADD VALUE`); acceptable since the set is small.
- **`concentration`**: parfum / eau-de-parfum / eau-de-toilette / eau-de-cologne /
  extrait / eau-fraiche / etc. Closed set but with edge cases ("body mist",
  "perfume oil"). Lean: lookup table `concentrations(id, slug, label)`
  rather than ENUM — easier to extend without migrations and contributors
  can add via PR.

### Q5. M:M `fragrance_notes` join — where does "role" live?

- Option A (denormalized in join): `fragrance_notes(fragrance_id, note_id,
  role ENUM('top','heart','base'), position INT NULL)` with PK
  `(fragrance_id, note_id, role)` — same note can appear in heart and base.
- Option B (three separate tables): `fragrance_top_notes`,
  `fragrance_heart_notes`, `fragrance_base_notes`.
- Option C (single boolean per role): `fragrance_notes(fragrance_id,
  note_id, is_top, is_heart, is_base)`.

Lean: **Option A** — single join with a `role` enum column. Standard,
indexable, queryable. Add a `position` int for ordering within a role
(some catalogs surface "first note in top: bergamot"). PK
`(fragrance_id, note_id, role)`.

### Q6. Embeddings: one row per fragrance vs separate "views"

- **One row per fragrance** (`fragrance_embeddings(fragrance_id PK,
  embedding vector(512), model TEXT, source_hash TEXT)`) — simple.
- **Multiple rows per fragrance keyed by view** (`fragrance_embeddings(id,
  fragrance_id, view ENUM('description','notes','combined'), embedding,
  model, source_hash)`) — supports hybrid retrieval (rerank using
  notes-only embedding alongside description-only).

Lean: **one row per fragrance for v1**, single combined view (concat
`name`, `brand`, `concentration`, `notes`, `description`). Add a `view`
column from day 1 with default `'combined'` and a UNIQUE
(`fragrance_id`, `view`) — that way moving to multi-view later is a pure
data migration, no schema change. Alternative: skip `view` and add it
later via Alembic — also fine and simpler. Decide.

### Q7. Articles — relationship to fragrances?

The brief lists `articles` as a table but doesn't say what links them to
fragrances. Options:
- M:M `article_fragrances(article_id, fragrance_id)` — clean, supports
  "this article mentions Aventus and Bleu de Chanel."
- Tag-based (`articles.tags TEXT[]`) — cheaper but loses join.
- Both (M:M + denormalized topics for browse).

Lean: **M:M `article_fragrances`** plus an optional `articles.topics
TEXT[]` for free-form tags. Keep schema small; tags are nice-to-have.

### Q8. Multilingual content

Spec is EN-only for v1. **Confirm** we do NOT add `lang` columns or
translation tables. If multilingual lands later, `notes`/`accords` would
get a `<entity>_translations(entity_id, lang, label, description)` shape.
Flagging because once an `i18n.lang` column is in `fragrances`, retrofitting
existing translations is painful.

Lean: EN-only, no `lang` columns. Document as ADR.

### Q9. Single Alembic revision vs split (schema + indexes)

- **Single initial revision** — easiest to read, one `op.create_table` per
  table plus one block of `op.create_index`/`op.execute(CREATE INDEX ...
  USING hnsw)` calls and one `op.execute("CREATE EXTENSION IF NOT EXISTS
  vector")`. Down-migration drops everything.
- **Two revisions: schema, then indexes** — lets you tune HNSW params
  without rewriting schema, but on a fresh DB they always run together.
  Slight overhead.

Lean: **single revision**. Indexes will be tuned later via separate
revisions anyway; splitting day-1 just for that doesn't help.

### Q10. Async vs sync Alembic env.py

- **Sync** is the most battle-tested path; Alembic loads sync engine via
  `engine_from_config()`. App code stays async.
- **Async** uses `async_engine_from_config()` + `await connection.run_sync(
  do_run_migrations)` (verified via Context7 today). More aligned with the
  rest of the codebase.

Lean: **async env.py** — Context7 documents the pattern explicitly, the rest
of `apps/api` is async, and using sync alembic just for migrations adds a
second connection style for no benefit. Cost: slightly more env.py code,
asyncio.run() wrapper.

### Q11. Down-migrations: real rollback or NotImplementedError?

For the **initial revision**, "down" means drop every table + drop the
extension. Two takes:
- **Real down** (`op.drop_table` for each, `op.execute("DROP EXTENSION
  vector")`) — formally correct, lets `alembic downgrade base` clean a
  test DB.
- **`raise NotImplementedError`** — common in production teams; "we never
  go back to zero, fight me" is a valid stance.

Lean: **real down** for the initial revision specifically. Costs ~15 lines
in the migration file and makes the migration test (`alembic upgrade head
&& alembic downgrade base`) a useful smoke. Future revisions can be
`NotImplementedError` if we want.

### Q12. HNSW parameters

Verified via Context7 (pgvector README): default index is `CREATE INDEX ON
items USING hnsw (embedding vector_cosine_ops)` — no `m`/`ef_construction`
overrides means defaults `m=16`, `ef_construction=64` apply. Higher
`ef_construction` improves recall at build cost; doesn't matter for an empty
table. Query-time `ef_search` defaults to 40 and is set per-session via
`SET hnsw.ef_search = 100`.

Lean: **defaults for v1** (`m=16`, `ef_construction=64`, `vector_cosine_ops`).
Document a CONTRIBUTING note explaining how to bump for catalog growth.

### Q13. Ontology loader: `packages/ontology/` Python package vs `apps/api`-internal module

- **Sibling Python package** (`packages/ontology/pyproject.toml` declares
  `fragwise_ontology` package, importable from `apps/api` via
  `[tool.uv.sources] fragwise-ontology = { workspace = true }` + the
  workspace switch in `apps/api/pyproject.toml`). Pros: clean reuse,
  packageable to PyPI, used by future scripts that might not have the api
  installed. Cons: forces uv into workspace mode (per the 0b ADR-0006
  carry-forward) and adds a publishable artifact we don't need yet.
- **Module under `apps/api`** (`apps/api/src/fragwise_api/ontology/`).
  Pros: zero new packaging. Cons: violates the brief's stated location
  (`packages/ontology/`), couples ontology to the api app.
- **Hybrid**: data files live in `packages/ontology/{notes.yaml, accords.yaml,
  synonyms.json}` (no `pyproject.toml`), loader lives in
  `apps/api/src/fragwise_api/ontology/loader.py` and reads the YAML/JSON via
  a relative path. Pros: data is portable (CDNs, other languages), no uv
  workspace; loader is testable inside api. Cons: the data location is
  hard-coded relative to repo root in the loader (resolvable via env var).

Lean: **hybrid**. Keeps 0c surgical and avoids the uv workspace flip. The
ontology files are *data*, not *code*; "Python package" gates seem
premature.

### Q14. Ontology validation: pydantic v2 vs marshmallow vs raw dicts

Pydantic v2 is the modern default; FastAPI already uses it transitively in
0c (we'll add `pydantic` as a direct dep when we add `openai`/SQLAlchemy
2.0 wires anyway). Marshmallow is fine but a redundant dep. Raw dicts work
but you lose IDE help and runtime validation.

Lean: **pydantic v2** with `OntologyDocument(BaseModel)` types in `loader.py`.

### Q15. Ontology versioning

Include `version: 1` (or `schema: "fragwise.ontology/v1"`) in each YAML/JSON
file? Cheap forward-compat insurance; loader rejects unknown versions and
contributors get a clear error when the schema evolves.

Lean: **yes**, include `schema: "fragwise.ontology/v1"` at the top of every
ontology file, validate via pydantic.

### Q16. Example data realism

The brief asks for "~5 top-level note categories, ~20 example notes,
6 accord families, 30 synonyms." That's enough to ingest, query, and verify
embeddings flow without polluting the catalog with misinformation.

Lean: **~5 top-level note categories (citrus, woody, floral, oriental,
fresh) → ~20 leaf notes; 6 accord families; ~30 synonym pairs**. Drop a
header comment in each YAML saying "EXAMPLES — replace with curated data
in a follow-up phase."

### Q17. Embeddings — store model name?

Per row: `model TEXT NOT NULL` (e.g., `text-embedding-3-small@512`)?
Yes. Embedding-model drift is real (we'll bump to `text-embedding-4-*`
eventually). Knowing per-row which model produced which vector is the
only way to do partial backfills cleanly.

Lean: **yes, store `model` and `dimensions` on each row.**

### Q18. Embeddings idempotency: hash text vs `IS NULL` check

- `IS NULL` check: cheap, but "I changed the description" doesn't
  re-trigger.
- Hash: `source_hash TEXT NOT NULL` (sha256 of normalized input). Compare
  hash before re-embedding; skip if equal.

Lean: **hash-based** — store `source_hash`. The embed script computes
hash, looks up existing row, skips if match.

### Q19. Embedding script execution model

For 0c, just a one-shot Python script (`uv run python data/scripts/embed_fragrances.py`).
Future shape: cron job, or queued worker (Celery/Arq/RQ) to embed on
fragrance insert. Flag for later, do not implement now.

### Q20. Embedding batch size

OpenAI accepts up to 2048 inputs per request; cost is per-token regardless.
Default 100 is conservative. Use `tenacity` for retry/backoff on 429.

Lean: **batch=100, exponential backoff via tenacity**, idempotency-key per
batch (the fragrance ids in the batch, comma-joined, hashed).

### Q21. Test approach: testcontainers vs CI postgres service vs running compose

| Path | Pros | Cons |
|---|---|---|
| `testcontainers-python` | Same code locally and in CI, no Docker network ops | Spawns Docker per test session (~3s warmup) |
| GH Actions `services.postgres` | Native, fast | Different fixture path local-vs-CI |
| Reuse running `docker compose` postgres | Fastest local | Tests pollute the dev DB; flaky |

Lean: **testcontainers in tests, CI uses the same fixture**. CI workflow
will need Docker available (it is by default on `ubuntu-latest` GitHub
runners). Use `pgvector/pgvector:pg16` as the testcontainer image so the
extension is preinstalled. Verified via Context7: `PostgresContainer(
image="pgvector/pgvector:pg16", driver="asyncpg")` returns a usable
`get_connection_url()`.

### Q22. CI postgres step: run migrations as part of api.yml

Need to either (a) attach `services.postgres` and run alembic against it,
or (b) just trust the testcontainers-based test. Lean: testcontainers
covers it. Adding `services.postgres` separately would be redundant and
costs ~20s of CI per run.

Final lean: **drop the originally-proposed "spin up postgres service +
alembic upgrade" step** — instead, the migration test (using
testcontainers) does the same thing inside pytest and runs as part of the
existing `pytest` step. Keeps `api.yml` short.

### Q23. Permitted-paths widening

The 0b design said: "0c will ship its own delta to repo-skeleton listing
the data/scripts and migrations paths it needs." That delta MUST include:

- `data/scripts/**/*.py`
- `data/seed/**/*.{yaml,json}` (or whatever format we pick)
- `packages/ontology/**/*.{yaml,json,md,py}` (per Q13's hybrid lean, the
  `.py` allowance only matters if we promote ontology to a package later;
  for now allowing it is forward-compatible at zero cost)
- `apps/api/alembic/**`
- `apps/api/alembic.ini`

Lean: **include all of the above** in the delta plus a forward-compat note.

### Q24. `/readyz` endpoint?

The 0b design said `/readyz` (deep ping incl. DB) lands when DB connections
exist — i.e., 0c. The brief for 0c doesn't explicitly call it out but it
falls out naturally now that lifespan owns an engine.

Lean: **add `/readyz`** — runs `SELECT 1` against the engine, returns
`{"status":"ready"}` on success, 503 on failure. Tiny addition; closes the
0b carry-forward cleanly. Document as part of the api-app delta.

### Q25. pgvector image: extension auto-create on init?

The `pgvector/pgvector:pg16` image installs the extension binary but does
NOT run `CREATE EXTENSION` automatically — that has to happen per-database.
Two options:
- (a) Migration runs `CREATE EXTENSION IF NOT EXISTS vector` (lean — same
  in dev/CI/prod).
- (b) Add an entrypoint init script in compose (`./infra/db/init.sql`)
  that runs `CREATE EXTENSION` on first DB creation.

Lean: **(a) migration owns the extension creation**, no compose changes.
This keeps Neon-prod (where you can't drop init scripts in) and dev
identical.

### Q26. SQLAlchemy declarative base type — `DeclarativeBase` vs `MappedAsDataclass`

SA 2.0 supports `Base(DeclarativeBase)` (classic), `Base(DeclarativeBase,
AsyncAttrs)` for async lazy-load on instances, and
`Base(MappedAsDataclass)` for dataclass-style models. Verified via
Context7: `class Base(AsyncAttrs, DeclarativeBase): pass` is the canonical
async pattern.

Lean: **`AsyncAttrs + DeclarativeBase`**, explicit `Mapped[...]` type
annotations. No dataclass. Mypy strict will be happy.

### Q27. `pgvector` Python bindings

There's a `pgvector` PyPI package providing `pgvector.sqlalchemy.Vector`
type for column declaration. Verified: `Column(Vector(512))` is the
idiomatic SQLAlchemy way to declare a pgvector column.

Lean: **use `pgvector` package**, declare `embedding: Mapped[list[float]]
= mapped_column(Vector(512))`.

## Risks

- **R1 — pgvector autogenerate gap (carry from phase-0 R3)**: `alembic
  revision --autogenerate` does not detect the `Vector(...)` column type
  reliably and definitely doesn't emit `CREATE EXTENSION` or
  `CREATE INDEX ... USING hnsw`. Mitigation: hand-write the initial
  revision; document this in CONTRIBUTING.
- **R2 — testcontainers needs Docker on `ubuntu-latest` runners**: GitHub
  Actions runners ship Docker, so this works. But contributors on Windows
  without Docker Desktop will hit failures locally. Mitigation: documented
  prerequisite in CONTRIBUTING and a clear pytest skip if Docker is not
  reachable (`testcontainers` raises a clear exception today).
- **R3 — `OPENAI_API_KEY` in CI**: the embedding script must NOT run in CI.
  Mitigation: never call `embed_fragrances.py` from CI; tests for
  embeddings either skip when `OPENAI_API_KEY` is absent or use a
  fixture-recorded response (consider pytest-recording / VCR.py for
  later). For 0c lean: skip the live OpenAI test; only unit-test the
  hashing + idempotency logic with a stubbed embedder.
- **R4 — uv workspace flip if ontology becomes a package**: per Q13 lean
  (hybrid), this is avoided. If we change our minds and promote ontology
  to a package, the 0b ADR-0006 explicitly notes the workspace migration
  is mechanical.
- **R5 — Vector dimension lock-in**: 512 is decided in phase-0
  exploration U3. Changing later requires a destructive migration on
  `fragrance_embeddings`. Mitigation: store `dimensions` per row and
  cap the column at the chosen value; migration patterns for re-embedding
  are well-understood.
- **R6 — Alembic + asyncio gotcha**: `asyncio.run()` inside an already-
  running loop fails. The async env.py template handles this correctly;
  the risk is for someone running migrations from inside a Jupyter or
  pre-existing event loop. Mitigation: doc note. Verified via Context7
  that the canonical async env.py uses `asyncio.run(run_async_migrations())`.
- **R7 — HNSW build time on growing catalogs**: instant on empty schema;
  ~minutes once catalog hits 100k rows; concurrent builds (`CREATE INDEX
  CONCURRENTLY`) help. Flag for ops phase, not 0c blocker.
- **R8 — Seed data re-running pollutes dev DB**: ingest/seed scripts MUST
  be idempotent (`ON CONFLICT DO NOTHING` or upsert by slug). Catching
  this with a test that runs the script twice and asserts row count is
  trivial.
- **R9 — pgvector image tag drift**: 0b ADR-0009 pins `pgvector/pgvector:
  pg16` for Neon parity. Testcontainers must use the SAME image tag.
  Mitigation: a single constant in `tests/conftest.py` (e.g.,
  `PGVECTOR_IMAGE = "pgvector/pgvector:pg16"`).
- **R10 — Migration test needs to pass even when contributors don't have
  Docker locally**: `pytest` should still pass on the rest of the suite.
  Mitigation: use a pytest marker `@pytest.mark.integration` or
  `@pytest.mark.docker`, configure `addopts = "-m 'not integration'"`
  default; CI runs with `-m integration` to opt in. Or use auto-skip if
  `docker` is unreachable.
- **R11 — SQLAlchemy 2.x mypy plugin no longer required** (2.0 has built-in
  PEP 484 support via `Mapped[T]`). Verified via Context7. Mitigation: do
  NOT add `[tool.mypy] plugins = ["sqlalchemy.ext.mypy.plugin"]` — that's
  legacy 1.x advice.
- **R12 — `alembic` CLI vs `uv run alembic`**: alembic is invoked from
  `apps/api/` so the venv has the package + the migration env.py imports
  the project's `Base.metadata`. Mitigation: justfile recipes always run
  `cd apps/api && uv run alembic upgrade head` etc.
- **R13 — ENUM evolution friction**: adding values to a Postgres ENUM in a
  transaction-bound Alembic migration requires `ALTER TYPE ... ADD VALUE`
  which can't run inside a transaction in older Postgres. PG16 lifts this
  for `IF NOT EXISTS`. Acceptable; document.

## Trade-offs Worth Surfacing

- **UUID v7 vs BIGSERIAL** (Q1): distributed-friendliness vs index size +
  URL ergonomics. The project is OSS with expected forks dumping data —
  UUIDs lean toward v7. PG16 needs an extension or Python-side generation
  for UUIDv7.
- **Single Alembic revision vs split**: simplicity vs flexibility. Single
  wins at v1.
- **Async vs sync Alembic env.py**: codebase parity vs more-tested path.
  Async wins at v1 (Context7 documents the pattern explicitly).
- **`packages/ontology/` as Python package vs hybrid data-only** (Q13):
  reuse + portability vs zero-new-packaging. Hybrid wins.
- **One embedding row per fragrance vs multi-view**: simplicity vs hybrid
  retrieval. Single row + reserved `view` column for forward compat.
- **Soft delete vs hard delete**: audit trail vs storage hygiene. Hard
  wins for a public catalog.
- **testcontainers vs GH services postgres**: parity local-vs-CI vs raw
  speed. testcontainers wins at v1.
- **Native Postgres ENUM vs lookup table**: ergonomic SQL vs evolution
  cost. Mixed: ENUM for `gender`, lookup for `concentration` based on Q4
  lean.
- **`/readyz` in 0c (deep DB ping) vs deferring**: adds a few lines now,
  removes a 0b carry-forward note. Add it.

## Splits — recommend keeping unified

The original brief proposed three splits:

- 0c-1: schema + Alembic + DB session wiring (~6 file groups, ~15 tasks)
- 0c-2: ontology + ingestion script (~4 file groups, ~10 tasks)
- 0c-3: embeddings script + integration test (~3 file groups, ~8 tasks)

Arguments **for** splitting:
- Cleaner PR diffs (~30-45 files in unified vs ~10-15 per split).
- Earlier validation of schema before ontology depends on it.
- Embedding script can be skipped/deferred if API-key story isn't ready.

Arguments **against** splitting:
- Each split is itself small enough (10-15 tasks) that the SDD overhead
  per change (proposal + spec + design + tasks + apply + verify + archive)
  approaches the cost of the actual work.
- Schema, ontology, and embeddings reference each other — `notes` table
  is consumed by `ingest_ontology.py`; `fragrances` is consumed by
  `embed_fragrances.py`. Splitting forces stub interfaces between them
  that get torn down in the next change.
- The full 0c is still smaller than 0b (which was ~50 files and shipped
  as a single change cleanly).
- Repo-skeleton permitted-paths delta is shared across all three splits;
  splitting forces three deltas to the same spec or a bundled delta with
  a single permitted-paths owner — awkward.

**Recommendation: keep 0c unified.** Slot it as one change with three
tasks.md sections (schema, ontology, embeddings/CI). If the implementation
phase blows up, splitting at `sdd-apply` time is mechanical (one PR per
section against the same change folder). The unified path also matches
the cadence the user has set with 0a (1 change, 8 phases) and 0b (1
change, ~50 files, 7 phases).

If the user later disagrees, the cleanest split is 2-way:
- **0c-1**: schema + Alembic + DB session wiring + repo-skeleton
  permitted-paths delta + `/readyz` + DB tests.
- **0c-2**: ontology + ingest scripts + embedding script + their tests.

Avoid 3-way; the embedding/ingestion separation isn't load-bearing.

## Recommendation

Proceed to `sdd-propose phase-0c-schema-and-ontology` as a single unified
change. Block the proposal on closing **Q1 (UUID v7 vs BIGSERIAL)**,
**Q4 (year/gender/concentration shape)**, **Q6 (single embedding row vs
multi-view)**, and **Q24 (ship `/readyz` now or defer)** with the user.
The remaining Qs have lean answers that are likely fine at proposal time;
revisit at `sdd-design`.

Versions to pin in proposal/design (verified via Context7 on 2026-05-06,
adjust if newer at proposal time):

- `sqlalchemy[asyncio]>=2.0,<3.0` (latest stable per Context7)
- `asyncpg>=0.30,<1.0`
- `alembic>=1.13,<2.0`
- `pgvector>=0.3,<1.0` (Python package providing `pgvector.sqlalchemy.Vector`)
- `pydantic>=2.9,<3.0`
- `openai>=1.55,<3.0`
- `pyyaml>=6.0,<7.0`
- `tenacity>=9.0,<10.0`
- `python-slugify>=8.0,<9.0`
- `testcontainers[postgres]>=4.0,<5.0`
- `types-pyyaml>=6.0,<7.0` (dev)

## Ready for Proposal

**Partial.** Block on user decisions for Q1, Q4, Q6, Q24. Once those are
chosen, `sdd-propose phase-0c-schema-and-ontology` can run with this
exploration as input. Lean answers above can be adopted as defaults if the
user wants to skip the back-and-forth.

---

## Return Envelope

**Status**: success
**Executive Summary**: Exploration complete for `phase-0c-schema-and-ontology`.
27 unknowns surfaced (Q1-Q27) covering schema design (PK strategy, slugs,
timestamps, role placement on M:M, embeddings shape, articles linkage,
loose-typed columns, multilingual), Alembic mechanics (single vs split
revision, async env.py, down-migrations, HNSW params), ontology shape
(loader location, validation, versioning, example data realism),
embeddings ops (model column, idempotency hash, batch size, execution
model), testing (testcontainers vs CI service vs compose reuse), and
cross-cutting concerns (`/readyz`, permitted-paths widening, pgvector
extension creation, ENUM vs lookup tables). Each Q has a lean answer
ready to ratify at sdd-propose. **Recommend keeping 0c as one unified
change**, not splitting. Versions verified via Context7 on 2026-05-06
(SQLAlchemy 2.0 async + asyncpg, Alembic async env.py via
`async_engine_from_config`, pgvector HNSW with `vector_cosine_ops` and
defaults `m=16/ef_construction=64`, OpenAI `embeddings.create(model,
input, dimensions)`, testcontainers `PostgresContainer(image,driver)`).
Block sdd-propose on user decisions for Q1, Q4, Q6, Q24.
**Artifacts**:
- `openspec/changes/phase-0c-schema-and-ontology/exploration.md`
**Next Recommended**: User picks Q1 (PK), Q4 (loose columns), Q6
(embedding shape), Q24 (`/readyz` now?). Then run `sdd-propose
phase-0c-schema-and-ontology`.
**Risks**:
- R1 pgvector autogenerate gap — mitigated by hand-written initial revision
- R2 testcontainers needs Docker on contributors' machines — mitigated by
  CONTRIBUTING note + auto-skip
- R3 `OPENAI_API_KEY` MUST NOT run in CI — embed script never invoked from
  CI; embedding tests stub the embedder
- R5 vector dimension lock-in — store `dimensions` + `model` per row to
  enable clean re-embed migrations
- R6 Alembic asyncio.run inside an existing loop — documented; canonical
  env.py from Context7
- R8 ingest/seed re-run pollutes DB — idempotency tests required
- R10 contributors without Docker — `@pytest.mark.integration` opt-in
  marker
- R13 ENUM evolution friction — documented; PG16 supports `ADD VALUE IF
  NOT EXISTS`
