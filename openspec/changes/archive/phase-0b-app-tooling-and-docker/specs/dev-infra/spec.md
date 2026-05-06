# dev-infra Specification

## Purpose

Defines the local-development infrastructure: a `docker-compose.yml` providing Postgres (with pgvector) and Redis services for local-only use, and a `justfile` of orchestration recipes covering install, dev, test, lint, and database lifecycle.

## Requirements

### Requirement: Docker Compose Services

The repo-root `docker-compose.yml` MUST declare exactly two services: `postgres` and `redis`.

- `postgres` MUST use image `pgvector/pgvector:pg16` with an inline comment explaining the pin (Neon production parity).
- `postgres` MUST mount a named volume `fragwise-pgdata` for persistence and MUST expose port `5432:5432` on the host.
- `redis` MUST use image `redis:7-alpine`, mount a named volume (e.g. `fragwise-redisdata`), and MUST expose port `6379:6379` on the host.

#### Scenario: Compose services and pins are correct

- GIVEN `docker-compose.yml`
- WHEN parsing it as YAML
- THEN `services.postgres.image` equals `pgvector/pgvector:pg16`
- AND `services.redis.image` matches `redis:7-alpine`
- AND each service has a named volume and the listed host port mapping
- AND a comment line near the postgres image references the Neon parity reason

### Requirement: No Production-Mode Services In Compose

`docker-compose.yml` MUST NOT declare services that target production deploy targets (no Vercel mocks, no Fly.io launchers, no application web/api services). Compose is local-dev only — production runs on Vercel + Fly.io + Neon + Upstash.

#### Scenario: Only postgres and redis are defined

- GIVEN `docker-compose.yml`
- WHEN listing keys under `services:`
- THEN the set of service names is exactly `{postgres, redis}`

### Requirement: Justfile Recipes Defined

The repo-root `justfile` MUST define recipes named `install`, `dev`, `dev-web`, `dev-api`, `test`, `test-web`, `test-api`, `lint`, `lint-web`, `lint-api`, `db-up`, `db-down`, and `db-shell`. Each recipe MUST be preceded by a one-line comment header explaining its purpose.

#### Scenario: All required recipes are present and documented

- GIVEN `justfile`
- WHEN running `just --list`
- THEN every required recipe name appears in the output
- AND inspecting the file shows a `# ...` comment line immediately preceding each recipe declaration

### Requirement: Database Recipes Wrap Compose

The `db-up` recipe MUST run `docker compose up -d postgres redis`. The `db-down` recipe MUST run `docker compose down` (without `-v`, to preserve volumes). The `db-shell` recipe MUST exec `psql` inside the running `postgres` container.

#### Scenario: db-up brings up postgres and redis detached

- GIVEN no compose stack is running
- WHEN running `just db-up`
- THEN `docker compose ps` shows `postgres` and `redis` in `running` state
- AND no other compose services are started

#### Scenario: db-down preserves volumes

- GIVEN the compose stack is running with data in `fragwise-pgdata`
- WHEN running `just db-down`
- THEN both containers stop and are removed
- AND the `fragwise-pgdata` volume still exists (`docker volume ls` includes it)

### Requirement: Just Install Provisions Both Toolchains

`just install`, when run from a fresh clone with `pnpm`, `uv`, and `node` available on PATH, MUST install both the JS workspace and the Python project.

#### Scenario: install populates node_modules and api venv

- GIVEN a fresh clone with no `node_modules/` and no `apps/api/.venv/`
- WHEN running `just install`
- THEN `apps/web/node_modules/` (or workspace root `node_modules/`) is populated
- AND `apps/api/.venv/` exists with installed Python packages
- AND the recipe exits 0
