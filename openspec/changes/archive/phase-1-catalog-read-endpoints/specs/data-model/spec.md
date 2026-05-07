# Delta for data-model

## ADDED Requirements

### Requirement: Fragrance-Accords Join Table

The schema MUST declare a `fragrance_accords` join table with columns: `id` UUID PK, `fragrance_id` UUID NOT NULL REFERENCES `fragrances.id`, `accord_id` UUID NOT NULL REFERENCES `accords.id`, `created_at` TIMESTAMPTZ NOT NULL DEFAULT `now()`. A UNIQUE constraint MUST exist on `(fragrance_id, accord_id)`. B-tree indexes MUST exist on `fragrance_id` and on `accord_id`.

#### Scenario: Table created with constraints

- GIVEN the new migration has been applied
- WHEN inspecting `\d fragrance_accords`
- THEN columns `id`, `fragrance_id`, `accord_id`, `created_at` are present with the declared types and FKs
- AND a UNIQUE index on `(fragrance_id, accord_id)` is present
- AND B-tree indexes on `fragrance_id` and `accord_id` are present

#### Scenario: Duplicate pair rejected

- GIVEN a row `(fragrance_id=F, accord_id=A)` exists in `fragrance_accords`
- WHEN inserting a second row with the same `(F, A)` pair
- THEN the insert fails with a unique-constraint violation

### Requirement: ORM Relationship Declarations For Catalog Read Endpoints

The SQLAlchemy ORM models MUST declare the following relationships so eager loading (`selectinload`/`joinedload`) works without lazy I/O on the async session.

- `Fragrance.notes` — many-to-many via `fragrance_notes`, with the `role` column accessible (Association proxy or explicit `FragranceNote` association object).
- `Fragrance.perfumers` — many-to-many via `fragrance_perfumers`.
- `Fragrance.accords` — many-to-many via the new `fragrance_accords`.
- `Fragrance.articles` — many-to-many via `fragrance_articles` (the table exists per the initial migration).
- `Note.parent` — self-referential many-to-one via `parent_id`.
- `Note.children` — self-referential one-to-many (reverse of `parent`).
- Reverse-side collections: `Brand.fragrances`, `Perfumer.fragrances`, `Accord.fragrances`, `Note.fragrances`.

These additions MUST NOT alter any existing column, index, or FK; they are ORM-only.

#### Scenario: Eager-loaded fragrance detail

- GIVEN `fragrance_accords` is migrated and ORM relationships are declared
- WHEN executing `select(Fragrance).options(selectinload(Fragrance.notes), selectinload(Fragrance.perfumers), selectinload(Fragrance.accords), selectinload(Fragrance.articles), joinedload(Fragrance.brand), joinedload(Fragrance.concentration)).where(Fragrance.slug == 'aventus')`
- THEN the query succeeds
- AND accessing `frag.notes`, `frag.perfumers`, `frag.accords`, `frag.articles` from the result raises no `MissingGreenlet`

#### Scenario: Note tree assembly via parent/children

- GIVEN a parent note `citrus` and a child note `bergamot` exist
- WHEN executing `select(Note).options(selectinload(Note.children))` and accessing `note.children` on the citrus row
- THEN the children collection contains `bergamot`
- AND on `bergamot`, accessing `note.parent` returns the citrus row without lazy I/O

### Requirement: Alembic Revision 0002 — Fragrance Accords

A new Alembic revision file `apps/api/alembic/versions/0002_fragrance_accords.py` MUST exist. Its `upgrade()` MUST create the `fragrance_accords` table and the required indexes. Its `downgrade()` MUST drop the indexes and the table. The revision MUST NOT touch the `vector` extension (already present from revision `0001`).

#### Scenario: Upgrade then downgrade is reversible

- GIVEN the database is at revision `0001` (initial)
- WHEN running `alembic upgrade head`
- THEN the migration to `0002` succeeds
- AND `\d fragrance_accords` shows the table with declared columns and indexes
- WHEN running `alembic downgrade -1`
- THEN the database returns to revision `0001`
- AND `fragrance_accords` is dropped
- AND no other tables, indexes, or extensions are affected
