# Proposal: phase-0c-schema-and-ontology

## Intent

Land the data foundation: SQLAlchemy 2.0 + asyncpg models, Alembic
migrations (pgvector + HNSW), DB session in the FastAPI lifespan,
ontology files + loader, and ingestion script skeletons. Closes the 0b
carry-forwards (`/readyz`, repo-skeleton permitted-paths widening) and
unblocks every feature phase that needs catalog data.

## Scope

### In Scope
- DB models under `apps/api/src/fragwise_api/db/models/` — UUID v7 PKs
  everywhere (Q1), gender PG ENUM, concentration lookup table,
  `year_released` int + nullable `year_text` (Q4), `fragrance_notes`
  with `role` ENUM (Q5), `fragrance_embeddings` with reserved `view`
  column (Q6).
- Alembic at `apps/api/alembic/` — async `env.py`, hand-written
  `0001_initial.py` (pgvector ext, HNSW `m=16, ef_construction=64`,
  FTS, real down-migration; Q9-Q12, Q25).
- DB session wiring in `lifespan()` + FastAPI dependency
  (`apps/api/src/fragwise_api/db/session.py`).
- `/readyz` endpoint with `SELECT 1` probe (Q24).
- Ontology hybrid layout (Q13): data at `packages/ontology/{notes.yaml,
  accords.yaml, synonyms.json, schema.md}` with `version: 1` (Q15);
  pydantic v2 loader at `apps/api/src/fragwise_api/ontology/loader.py`
  (Q14, Q16).
- `data/scripts/`: `ingest_ontology.py`, `seed_minimal_fragrances.py`,
  `embed_fragrances.py` — all idempotent via slug + `source_hash`
  (Q18-Q20).
- Integration tests using testcontainers (`pgvector/pgvector:pg16`,
  `@pytest.mark.integration` opt-in; Q21-Q22).
- `justfile` recipes: `db-migrate`, `db-rollback`, `db-reset`,
  `ingest`, `embed`, `test-integration`.
- Dep additions in `apps/api/pyproject.toml`; minor `docker-compose.yml`
  fix (`POSTGRES_DB=fragwise`).

### Out of Scope
- Real catalog/ontology data (only ~10 example fragrances).
- Catalog API endpoints, search/retrieval, LangGraph DB integration,
  Clerk auth, admin UI.
- CI step that calls OpenAI (embed script is local-only; R3).

## Capabilities

### New Capabilities
- `data-model`: schema, indexes, embedding row shape, ontology format.
- `ingestion`: `data/scripts/` contracts and idempotency rules.

### Modified Capabilities
- `api-app`: add `/readyz`, DB session lifecycle, Alembic-applies-cleanly,
  ontology loader exists.
- `repo-skeleton`: widen permitted paths to `data/scripts/**`,
  `data/seed/**`, `packages/ontology/**`, `apps/api/alembic/**`,
  `apps/api/alembic.ini` (closes 0b carry-forward; Q23).

## Approach

Hand-written async Alembic initial revision (autogenerate can't see
pgvector — R1). Single revision (Q9) with real `downgrade` (Q11). UUID
v7 generated Python-side (PG16 lacks native `uuidv7()`). Embeddings
pinned to `text-embedding-3-small@512`; row stores `model`,
`dimensions`, `source_hash`. Testcontainers for integration tests
inside pytest — drops the redundant CI postgres-service step (Q22).

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `apps/api/src/fragwise_api/db/` | New | Models, session, base. |
| `apps/api/alembic/`, `apps/api/alembic.ini` | New | Async env, initial revision. |
| `apps/api/src/fragwise_api/ontology/loader.py` | New | Pydantic v2 loader. |
| `apps/api/src/fragwise_api/main.py` | Modified | Lifespan engine, `/readyz`. |
| `packages/ontology/` | New content | YAML/JSON + schema.md. |
| `data/scripts/`, `data/seed/` | New | Ingest, seed, embed. |
| `apps/api/tests/integration/` | New | Testcontainers fixtures. |
| `apps/api/pyproject.toml` | Modified | SQLAlchemy, asyncpg, Alembic, pgvector, pydantic, openai, pyyaml, tenacity, testcontainers. |
| `docker-compose.yml`, `justfile` | Modified | `POSTGRES_DB`, 6 new recipes. |
| `openspec/specs/{api-app, repo-skeleton}/spec.md` | Modified | Deltas. |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| R1 pgvector autogenerate gap | High | Hand-written initial revision. |
| R2 testcontainers needs Docker | Med | Opt-in marker; CONTRIBUTING note. |
| R3 OPENAI_API_KEY in CI | Low | Embed script never invoked from CI; tests stub embedder. |
| R5 Vector dim lock-in (512) | Low | Store `model`/`dimensions`/`source_hash` per row. |
| R8 Re-runs polluting dev DB | Med | Idempotent UPSERT on slug + hash. |
| R13 ENUM evolution friction | Low | PG16 supports `ADD VALUE IF NOT EXISTS`; document. |

## Rollback Plan

- Pre-merge: `git reset`.
- Post-merge, pre-deploy: revert merge commit; no production state.
- Post-deploy: revert migration. The down-migration drops everything
  (schema is brand new in 0c — nothing below it to preserve).

## Dependencies

- Phase 0a (repo skeleton) and 0b (app tooling + Docker) archived.
- Docker available locally for integration tests (CI runners ship it).

## Success Criteria

- [ ] `just db-migrate` applies cleanly against the dev DB; `db-rollback`
      drops cleanly.
- [ ] `pytest -m integration` passes via testcontainers.
- [ ] `/readyz` returns 200 with DB up, 503 with DB down.
- [ ] `ingest_ontology.py` and `seed_minimal_fragrances.py` re-runs are
      no-ops (idempotency test).
- [ ] `embed_fragrances.py` skips rows whose `source_hash` matches.
- [ ] `repo-skeleton` permitted paths cover all newly-created files.
