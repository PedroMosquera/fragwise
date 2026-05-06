# Delta for repo-skeleton

## MODIFIED Requirements

### Requirement: Application Code And Build Tooling Allowed Under Defined Paths

The repository MAY contain application source files, build/dev tooling, schema migrations, ontology data, and operator scripts under explicitly permitted paths only. Permitted locations:

- `apps/web/**` — TypeScript/TSX source, Next.js config, PostCSS config, ESLint flat config, Prettier config, vitest config, Playwright config, `package.json`.
- `apps/api/**` — Python source, `pyproject.toml`, `uv.lock`, `Dockerfile`, ruff/mypy/pytest config.
- `apps/api/alembic/**` — Alembic environment, script template, and revision files (Python).
- `apps/api/alembic.ini` — Alembic configuration file at the api project root.
- `data/scripts/**` — Python operator scripts for ingestion, seeding, and embeddings, plus optional `README.md` / `__init__.py`.
- `data/seed/**` — Seed datasets in YAML or JSON consumed by `data/scripts/`.
- `packages/ontology/**` — Ontology data files (`notes.yaml`, `accords.yaml`, `synonyms.json`), schema docs (`schema.md`), and (optional, forward-compatible) Python files if ontology is later promoted to a sibling package.
- Repo root — `docker-compose.yml`, `justfile`.
- `.github/workflows/**` — GitHub Actions workflow YAML files.

Outside these paths, the original 0a constraints still hold (no stray `*.ts`, `*.tsx`, `*.py`, `*.sql`, `Dockerfile`, `Makefile`, or workflow files).

(Previously: 0b permitted `apps/web/**`, `apps/api/**`, repo-root `docker-compose.yml` and `justfile`, and `.github/workflows/**`. 0c additionally permits `apps/api/alembic/**`, `apps/api/alembic.ini`, `data/scripts/**`, `data/seed/**`, and `packages/ontology/**` content — closing the 0b carry-forward.)

#### Scenario: Permitted application and tooling files exist under defined paths

- GIVEN a fresh clone after 0c lands
- WHEN running `git ls-files`
- THEN files matching `apps/web/**/*.{ts,tsx}`, `apps/api/**/*.py`, `apps/api/Dockerfile`, `apps/api/alembic/**/*.py`, `apps/api/alembic.ini`, `data/scripts/**/*.py`, `data/seed/**/*.{yaml,json}`, `packages/ontology/**/*.{yaml,json,md,py}`, repo-root `docker-compose.yml`, repo-root `justfile`, and `.github/workflows/*.yml` MAY be present
- AND no `*.ts`, `*.tsx`, `*.py`, `*.sql`, `Dockerfile`, or workflow file exists outside those permitted paths

#### Scenario: Stray application file outside permitted paths is forbidden

- GIVEN a fresh clone
- WHEN searching for `*.ts`, `*.tsx`, or `*.py` files outside `apps/**`, `data/scripts/**`, `data/seed/**`, and `packages/ontology/**`
- THEN no such files are tracked
- AND searching for a `Makefile` at the repo root returns nothing
