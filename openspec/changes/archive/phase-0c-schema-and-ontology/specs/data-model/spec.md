# data-model Specification

## Purpose

Defines the relational + vector schema for Fragwise: tables, primary key strategy, lookup contents, hierarchical notes, M:M joins, embedding row shape, indexes (B-tree, GIN/FTS, HNSW), the pgvector extension contract, the initial Alembic migration's down-migration contract, and the on-disk ontology file format consumed by ingestion.

## Requirements

### Requirement: UUID v7 Primary Keys Everywhere

Every table in the schema MUST use a `UUID` primary key column named `id`. UUIDs MUST be generated Python-side as UUID v7 (time-sortable). PG16 lacks native `uuidv7()`; the Python application MUST supply the UUID at insert time.

#### Scenario: Inserted row has a valid UUID PK

- GIVEN the migrations have been applied to an empty Postgres+pgvector DB
- WHEN inserting a row into any entity table via the application
- THEN the resulting row's `id` column is a string of length 36 matching the UUID format `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- AND the value parses cleanly through `uuid.UUID(...)`

### Requirement: Tables Present In Initial Migration

The initial Alembic revision MUST create the following tables: `brands`, `perfumers`, `fragrances`, `notes`, `accords`, `concentrations`, `articles`, `fragrance_notes`, `fragrance_perfumers`, `fragrance_articles`, `fragrance_embeddings`. Tables MUST be created in dependency order so foreign keys resolve.

#### Scenario: All 11 tables exist after migration

- GIVEN an empty Postgres+pgvector DB
- WHEN running `alembic upgrade head`
- THEN `SELECT tablename FROM pg_tables WHERE schemaname='public'` returns at minimum the 11 tables listed above
- AND every M:M join table has FK constraints on its parent IDs

### Requirement: Common Entity Columns

Every content entity table (`brands`, `perfumers`, `fragrances`, `notes`, `accords`, `articles`, `concentrations`) MUST declare `id` UUID PK, `created_at` TIMESTAMPTZ NOT NULL DEFAULT `now()`, `updated_at` TIMESTAMPTZ NOT NULL DEFAULT `now()` with `onupdate=now()`, and `slug` TEXT UNIQUE NOT NULL.

#### Scenario: Every content table has the common columns

- GIVEN the migrations are applied
- WHEN running `\d <table>` for each content entity
- THEN columns `id`, `created_at`, `updated_at`, `slug` are present
- AND `slug` has a UNIQUE index
- AND `updated_at` is bumped automatically when a row is updated through SQLAlchemy

### Requirement: Fragrance Table Fields

The `fragrances` table MUST declare: `id` UUID PK, `slug` TEXT UNIQUE NOT NULL, `name` TEXT NOT NULL, `brand_id` UUID NOT NULL REFERENCES `brands.id`, `year_released` INTEGER NULLABLE, `year_text` TEXT NULLABLE, `gender` ENUM (`masc`, `fem`, `unisex`, `genderfree`) NOT NULL, `concentration_id` UUID NULLABLE REFERENCES `concentrations.id`, `description` TEXT NULLABLE.

#### Scenario: Fragrance row honors the column contract

- GIVEN the migrations are applied
- WHEN inserting a fragrance with `name='Aventus'`, `gender='masc'`, `year_released=2010`, `year_text=NULL`
- THEN the insert succeeds
- AND inserting a row with `gender='other'` (not in the ENUM) fails with a constraint error
- AND the `brand_id` MUST resolve to an existing brand row or the insert fails

### Requirement: Concentration Lookup Seeded

The `concentrations` table MUST be seeded by the initial migration (or `ingest_ontology.py`) with at least the following slugs: `edp`, `edt`, `cologne`, `parfum`, `extrait`. Each row MUST have a `name` column populated.

#### Scenario: Lookup rows present after ingest

- GIVEN the schema has been migrated and ontology ingested
- WHEN running `SELECT slug FROM concentrations`
- THEN the result includes at least `edp`, `edt`, `cologne`, `parfum`, `extrait`
- AND every row has a non-null, non-empty `name`

### Requirement: Note Hierarchy

The `notes` table MUST declare `id` UUID PK, `slug` TEXT UNIQUE NOT NULL, `name` TEXT NOT NULL, and `parent_id` UUID NULLABLE REFERENCES `notes.id`. The `parent_id` self-FK enables hierarchies such as `bergamot → citrus`.

#### Scenario: A child note references a parent note

- GIVEN the `notes` table exists
- WHEN inserting a parent note `citrus` and a child note `bergamot` with `parent_id` set to citrus's id
- THEN both rows exist
- AND deleting the parent fails with a FK constraint error (no cascade) OR succeeds and nulls the child (per implementation), but the relationship is enforced

### Requirement: Accord Families Seeded

The `accords` table MUST declare `id` UUID PK, `slug` TEXT UNIQUE NOT NULL, `name` TEXT NOT NULL. The ontology seed MUST include at least: `chypre`, `fougere`, `oriental`, `gourmand`, `aquatic`, `woody`.

#### Scenario: Required accord families exist after ingest

- GIVEN ontology ingestion has run
- WHEN running `SELECT slug FROM accords`
- THEN the result includes all six required slugs

### Requirement: Fragrance-Notes Join With Role

The `fragrance_notes` join MUST declare `id` UUID PK, `fragrance_id` UUID FK NOT NULL, `note_id` UUID FK NOT NULL, `role` ENUM (`top`, `heart`, `base`) NOT NULL. A UNIQUE constraint MUST exist on `(fragrance_id, note_id, role)`. The same note MAY appear in multiple roles for the same fragrance.

#### Scenario: Same note can fill heart and base roles

- GIVEN a fragrance and a note exist
- WHEN inserting `(fragrance_id=F, note_id=N, role='heart')` and `(fragrance_id=F, note_id=N, role='base')`
- THEN both inserts succeed
- AND inserting a duplicate `(F, N, 'heart')` fails with a unique-constraint violation

### Requirement: Fragrance Embeddings Row Shape

The `fragrance_embeddings` table MUST declare: `id` UUID PK, `fragrance_id` UUID FK NOT NULL, `view` TEXT NOT NULL DEFAULT `'combined'`, `embedding` `vector(512)` NOT NULL, `model` TEXT NOT NULL, `dimensions` INTEGER NOT NULL, `source_hash` TEXT NOT NULL, `created_at` TIMESTAMPTZ NOT NULL DEFAULT `now()`. A UNIQUE constraint MUST exist on `(fragrance_id, view, model, dimensions)`.

#### Scenario: Embedding row stores model provenance

- GIVEN a fragrance row exists
- WHEN inserting a row with `model='text-embedding-3-small'`, `dimensions=512`, `source_hash='sha256...'`, `view='combined'`
- THEN the insert succeeds
- AND inserting a second row with the same `(fragrance_id, view, model, dimensions)` fails with a unique-constraint violation

### Requirement: HNSW Index On Embeddings

The `fragrance_embeddings.embedding` column MUST have an HNSW index using `vector_cosine_ops`, with parameters `m=16` and `ef_construction=64`. The index MUST be created by the initial migration via `op.execute("CREATE INDEX ... USING hnsw ...")`.

#### Scenario: HNSW index exists with documented params

- GIVEN migrations are applied
- WHEN inspecting `pg_indexes` for table `fragrance_embeddings`
- THEN an index using `hnsw` (`vector_cosine_ops`) exists
- AND the index definition includes `m=16` and `ef_construction=64` (or accepts the documented defaults)

### Requirement: B-tree Indexes On Slug And Foreign Keys

B-tree indexes MUST exist on `fragrances.slug`, `fragrances.brand_id`, `brands.slug`, `perfumers.slug`, `notes.slug`, `accords.slug`, and `articles.slug`.

#### Scenario: Slug and FK lookups have B-tree indexes

- GIVEN migrations are applied
- WHEN inspecting `pg_indexes` for each table above
- THEN a B-tree index on the listed column is present (UNIQUE indexes count as B-tree indexes)

### Requirement: Full-Text Search Index On Fragrances

The `fragrances` table MUST have a GIN index on `to_tsvector('english', name || ' ' || coalesce(description, ''))` (or an equivalent expression that combines `name` and `description`).

#### Scenario: FTS index lets us search fragrance names and descriptions

- GIVEN migrations are applied AND a fragrance with `name='Aventus'` and a description has been inserted
- WHEN running `SELECT id FROM fragrances WHERE to_tsvector('english', name || ' ' || coalesce(description, '')) @@ plainto_tsquery('english', 'aventus')`
- THEN the row is returned
- AND `EXPLAIN` shows the GIN index is used (or scannable with low row count)

### Requirement: pgvector Extension Created By Migration

The initial Alembic migration MUST execute `CREATE EXTENSION IF NOT EXISTS vector` before creating any `vector(...)` column. The compose init scripts and application code MUST NOT be responsible for creating the extension.

#### Scenario: Extension is owned by the migration

- GIVEN an empty Postgres+pgvector DB without the `vector` extension enabled
- WHEN running `alembic upgrade head`
- THEN the migration succeeds
- AND `SELECT extname FROM pg_extension` includes `vector`
- AND no compose init file or app-startup code calls `CREATE EXTENSION`

### Requirement: Initial Migration Down-Migration Drops Everything

The initial revision's `downgrade()` MUST drop all 11 tables, all created indexes, all created ENUM types (`fragrance_gender`, `fragrance_note_role`), and the `vector` extension. After downgrade, the database MUST be empty of project schema.

#### Scenario: Apply then rollback yields an empty database

- GIVEN an empty Postgres+pgvector DB
- WHEN running `alembic upgrade head` then `alembic downgrade base`
- THEN both commands exit 0
- AND `SELECT tablename FROM pg_tables WHERE schemaname='public'` returns no project tables
- AND `SELECT extname FROM pg_extension WHERE extname='vector'` returns no rows
- AND `SELECT typname FROM pg_type WHERE typname IN ('fragrance_gender','fragrance_note_role')` returns no rows

### Requirement: Ontology File Format Versioned

`packages/ontology/notes.yaml`, `packages/ontology/accords.yaml`, and `packages/ontology/synonyms.json` MUST each declare a top-level `version: 1` field. The ontology loader MUST reject files missing the `version` field with a clear error message.

#### Scenario: Ontology file without version field is rejected

- GIVEN a `notes.yaml` file present without a `version` field
- WHEN the loader is invoked on that file
- THEN the loader raises a `ValueError` (or pydantic `ValidationError`) referencing the missing `version` field
- AND no rows are inserted into the database
