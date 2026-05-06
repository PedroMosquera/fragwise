# Tasks: phase-0c-schema-and-ontology

References: paths and code snippets are in `design.md`. Each subtask cites the
section. Estimates assume an implementer with the full design loaded.

## Phase 1: Pre-flight

- [x] 1.1 Confirm 0a + 0b are archived, branch is clean, and no files in
      `design.md §"File Changes"` already exist (≠ `apps/api/main.py`,
      `pyproject.toml`, `docker-compose.yml`, `justfile`). (~3 min)

## Phase 2: Dependency updates

- [x] 2.1 Add the 9 runtime + 2 dev deps + pytest markers to
      `apps/api/pyproject.toml` per `design.md §"pyproject.toml diff"`,
      then `cd apps/api && uv sync` and commit `apps/api/uv.lock`. (~10 min)

## Phase 3: DB models

- [x] 3.1 Create `apps/api/src/fragwise_api/db/__init__.py` (exports
      `compute_source_hash`) and `db/base.py` (Base, `_uuid7`, UUIDMixin,
      TimestampMixin) per `design.md §"UUID v7 generator"` + §"source_hash". (~10 min)
- [x] 3.2 Create `db/enums.py` (`Gender`, `NoteRole` Python enums) per
      `design.md §"db/enums.py"`. (~5 min)
- [x] 3.3 Create `db/models/{brand,perfumer,concentration}.py` per
      `design.md §"Models — lookup tables"`. (~10 min)
- [x] 3.4 Create `db/models/{note,accord,article}.py` per
      `design.md §"Models — taxonomy + articles"`. (~10 min)
- [x] 3.5 Create `db/models/fragrance.py` (UUID, FKs, `year_released`,
      `year_text`, `gender` PG ENUM, `concentration_id`) per
      `design.md §"Models — db/models/fragrance.py (full)"`. (~10 min)
- [x] 3.6 Create `db/models/joins.py` (`FragranceNote` w/ `role` ENUM,
      `FragrancePerfumer`, `FragranceArticle`) per `design.md §"Models — joins"`. (~10 min)
- [x] 3.7 Create `db/models/embedding.py` (`vector(512)`, `view`, `model`,
      `dimensions`, `source_hash`, UNIQUE) + `db/models/__init__.py`
      re-exports per `design.md §"Models — embedding"`. (~10 min)

## Phase 4: DB session, lifespan, /readyz

- [x] 4.1 Create `db/session.py` (`make_engine`, `make_sessionmaker`,
      `get_session`, `_normalize`) per `design.md §"db/session.py (full)"`. (~10 min)
- [x] 4.2 Replace `apps/api/src/fragwise_api/main.py` with the lifespan-wired
      version (engine on `app.state`, dispose on shutdown) per
      `design.md §"main.py (full revised)"`. (~5 min)
- [x] 4.3 Confirm `/readyz` (200 ok / 503 unready with truncated error) is
      present in `main.py` per `design.md §"main.py"`. (~3 min)

## Phase 5: Alembic

- [x] 5.1 Create `apps/api/alembic.ini` per `design.md §"alembic.ini"`. (~5 min)
- [x] 5.2 Create `apps/api/alembic/env.py` (async, `async_engine_from_config`
      + `asyncio.run`) and `apps/api/alembic/script.py.mako` per
      `design.md §"alembic/env.py"` + §"script.py.mako". (~10 min)
- [x] 5.3 Create `apps/api/alembic/versions/0001_initial.py` — hand-written:
      `CREATE EXTENSION vector`, both PG ENUMs, all tables, B-tree + GIN FTS
      + HNSW (`m=16, ef_construction=64, vector_cosine_ops`), 5-row
      concentration seed, full `downgrade()` reversing every step. Per
      `design.md §"alembic/versions/0001_initial.py (full)"`. (~45 min)

## Phase 6: Ontology data + schema doc

- [x] 6.1 Create `packages/ontology/notes.yaml` (`version: 1`, ~5 top + ~20
      leaf), `accords.yaml` (`version: 1`, 6 families), `synonyms.json`
      (`version: 1`, ~30 entries) per `design.md §"Ontology files"`. (~15 min)
- [x] 6.2 Create `packages/ontology/schema.md` documenting YAML/JSON shape +
      `version` field per `design.md §"schema.md"`. (~10 min)

## Phase 7: Ontology loader

- [x] 7.1 Create `apps/api/src/fragwise_api/ontology/__init__.py` (empty) and
      `ontology/loader.py` (pydantic v2 `NoteRecord`, `AccordRecord`,
      `SynonymRecord` + 3 `load_*` functions raising on `version != 1`) per
      `design.md §"ontology/loader.py (full)"`. (~15 min)

## Phase 8: Ingestion scripts

- [x] 8.1 Create `data/scripts/__init__.py` + `data/scripts/README.md`
      (operator order, CI exclusion, `OPENAI_API_KEY` requirement) and
      `data/seed/minimal_fragrances.yaml` (~10 fragrances) per
      `design.md §"data/scripts/README.md"` + §"data/seed". (~15 min)
- [x] 8.2 Create `data/scripts/ingest_ontology.py` (loads YAML/JSON,
      idempotent UPSERT on slug for notes + accords, also stores
      synonyms) per `design.md §"data/scripts/ingest_ontology.py"`. (~20 min)
- [x] 8.3 Create `data/scripts/seed_minimal_fragrances.py` (UPSERT brands,
      perfumers, fragrances + joins; uses `compute_source_hash`;
      idempotent) per `design.md §"data/scripts/seed_minimal_fragrances.py"`. (~25 min)
- [x] 8.4 Create `data/scripts/embed_fragrances.py` (exits non-zero without
      `OPENAI_API_KEY`; tenacity retry; batches of 100; dimensions=512;
      skips rows whose `source_hash` matches existing embedding) per
      `design.md §"data/scripts/embed_fragrances.py"`. (~25 min)

## Phase 9: Integration tests

- [x] 9.1 Create `apps/api/tests/integration/__init__.py` and `conftest.py`
      (testcontainer `pgvector/pgvector:pg16` w/ `driver="asyncpg"`,
      session-scoped fixture that runs `alembic upgrade head`, per-test
      `AsyncSession` fixture) per `design.md §"tests/integration/conftest.py"`. (~25 min)
- [x] 9.2 Create `tests/integration/test_migrations.py` (upgrade head ⇒
      tables + extension + HNSW present; downgrade base ⇒ schema empty)
      per `design.md §"test_migrations.py"`. (~15 min)
- [x] 9.3 Create `tests/integration/test_db_session.py`,
      `test_readyz.py` (200 + 503 via engine swap), and
      `test_ontology_loader.py` (happy + version-mismatch errors) per
      `design.md §"tests/integration/*"`. (~25 min)

## Phase 10: Tooling

- [x] 10.1 Add the 6 `justfile` recipes (`db-migrate`, `db-rollback`,
      `db-reset`, `ingest`, `embed`, `test-integration`) per
      `design.md §"justfile additions"`. (~10 min)
- [x] 10.2 Verify `docker-compose.yml` has `POSTGRES_DB=fragwise` (already
      correct per design `§"File Changes"`); no edit if present. (~2 min)

## Phase 11: Self-check

- [x] 11.1 `cd apps/api && uv sync` succeeds clean; `pnpm-lock.yaml`
      untouched; `just test` (unit, default markers) green. (~5 min)
- [x] 11.2 `just test-integration` green if Docker is available. If Docker
      absent, mark PARTIAL and note for verify. Includes
      `alembic upgrade head` + `downgrade base` smoke via
      `test_migrations.py`. (~10 min)
- [x] 11.3 Local smoke: `just db-migrate && just ingest && just db-rollback`
      against the dev compose Postgres. Skip `just embed` unless
      `OPENAI_API_KEY` is set; document outcome. (~10 min)
