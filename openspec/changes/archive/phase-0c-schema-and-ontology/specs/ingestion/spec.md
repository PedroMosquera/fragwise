# ingestion Specification

## Purpose

Defines the three operator scripts under `data/scripts/` that populate the database from on-disk artifacts: `ingest_ontology.py` (notes + accords), `seed_minimal_fragrances.py` (~10 example fragrances for end-to-end testing), and `embed_fragrances.py` (OpenAI embeddings into `fragrance_embeddings`). All scripts MUST be idempotent. Scripts are invoked manually (or via `just`); they MUST NOT run in CI.

## Requirements

### Requirement: Ontology Ingest Script

`data/scripts/ingest_ontology.py` MUST load `packages/ontology/notes.yaml` and `packages/ontology/accords.yaml`, then UPSERT rows into the `notes` and `accords` tables keyed on `slug`. The script MUST update `name` and `parent_id` if they have changed since the last run.

#### Scenario: Re-running ingest is a no-op (idempotency)

- GIVEN `notes.yaml` and `accords.yaml` are present and the script has run once successfully
- WHEN running `python data/scripts/ingest_ontology.py` a second time without modifying the YAML files
- THEN the script exits 0
- AND `SELECT count(*) FROM notes` is unchanged from the first run
- AND `SELECT count(*) FROM accords` is unchanged from the first run
- AND no duplicate rows exist

#### Scenario: Modified ontology updates existing rows

- GIVEN `notes.yaml` has a note `bergamot` with `parent_id` resolving to `citrus`, and the script has run once
- WHEN editing the YAML to change `bergamot`'s display `name` to `"Bergamot (Italian)"` and re-running the script
- THEN the row's `name` column is updated to the new value
- AND the row's `id` (UUID PK) is unchanged
- AND no new row is created

### Requirement: Minimal Fragrances Seed Script

`data/scripts/seed_minimal_fragrances.py` MUST insert approximately 10 example fragrances (with associated brand, perfumer, and note references) by reading from `data/seed/minimal_fragrances.yaml` (or equivalent). The script MUST UPSERT keyed on the fragrance `slug`. The script MUST record a `source_hash` per fragrance computed from the seed entry's normalized content.

#### Scenario: Seed script is idempotent

- GIVEN `data/seed/minimal_fragrances.yaml` exists with ~10 fragrances and the script has run once
- WHEN running the seed script a second time without modifying the YAML
- THEN the script exits 0
- AND `SELECT count(*) FROM fragrances` is unchanged
- AND every fragrance row's `source_hash` matches the first run

#### Scenario: Seed script detects content drift via source_hash

- GIVEN the seed has run once
- WHEN editing one fragrance's `description` in the YAML and re-running the seed script
- THEN that fragrance row's `description` and `source_hash` are updated
- AND other fragrance rows are untouched

### Requirement: OpenAI Embedding Script

`data/scripts/embed_fragrances.py` MUST call OpenAI `client.embeddings.create(model="text-embedding-3-small", input=[...], dimensions=512)`. For each fragrance with NO matching `fragrance_embeddings` row OR a row whose `source_hash` is stale relative to the fragrance's current canonical input text, the script MUST compute a new embedding and UPSERT into `fragrance_embeddings`. The script MUST batch inputs (up to 2048 per OpenAI call). The script MUST use `tenacity` for retry/backoff on rate-limit (429) and transient errors. The script MUST read `OPENAI_API_KEY` from the environment and MUST fail loudly with a non-zero exit code and a clear error message if the key is missing.

#### Scenario: Missing API key fails fast

- GIVEN `OPENAI_API_KEY` is unset in the environment
- WHEN running `python data/scripts/embed_fragrances.py`
- THEN the script exits non-zero
- AND stderr contains a clear message naming `OPENAI_API_KEY`
- AND no OpenAI HTTP call is made

#### Scenario: Embed script skips up-to-date rows

- GIVEN every fragrance has a current embedding row whose `source_hash` matches the canonical input text
- WHEN running the embed script
- THEN the script exits 0
- AND no OpenAI HTTP call is made (verifiable via stub or HTTP recorder)
- AND `fragrance_embeddings` row count is unchanged

#### Scenario: Embed script processes new and stale rows in batches

- GIVEN three new fragrances were added by the seed script with no embeddings yet, and one existing fragrance's `source_hash` is now stale
- WHEN running the embed script
- THEN the script issues at most one OpenAI batch call containing four inputs (or batch size up to 2048)
- AND four `fragrance_embeddings` rows are upserted
- AND each row's `model='text-embedding-3-small'` and `dimensions=512`

### Requirement: Just Recipes For Ingestion

The repo-root `justfile` MUST expose recipes `just ingest`, `just seed`, and `just embed` that invoke the three scripts respectively. Recipes MUST run from `apps/api/` so the venv resolves the project's deps.

#### Scenario: Just recipes invoke the scripts

- GIVEN `just` and `uv` are installed and the api venv is synced
- WHEN running `just ingest`, `just seed`, then `just embed` in order against a migrated empty DB (with `OPENAI_API_KEY` set)
- THEN every recipe exits 0
- AND `notes`, `accords`, `fragrances`, and `fragrance_embeddings` tables are populated

### Requirement: Operator README For Script Ordering

`data/scripts/README.md` MUST document the canonical operator ordering: `just db-migrate` then `just ingest` then `just seed` then `just embed`. The README MUST note that scripts are NOT invoked from CI.

#### Scenario: README documents ordering and CI exclusion

- GIVEN `data/scripts/README.md` exists
- WHEN reading the file
- THEN it contains the ordered command list `just db-migrate`, `just ingest`, `just seed`, `just embed`
- AND it explicitly states scripts are not run in CI

### Requirement: Scripts Are Not Invoked From CI

The repository's GitHub Actions workflows under `.github/workflows/**` MUST NOT call any script in `data/scripts/`. Only the test suite (which uses testcontainers and stubbed embedders) runs in CI.

#### Scenario: CI workflows do not call ingestion scripts

- GIVEN `.github/workflows/api.yml` and any other workflow files
- WHEN searching the YAML for the strings `ingest_ontology.py`, `seed_minimal_fragrances.py`, or `embed_fragrances.py`
- THEN none of those strings appear in any workflow file
