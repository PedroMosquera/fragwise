# Delta for repo-skeleton

Phase 0a is pure scaffolding — no runtime behavior. These are testable invariants on repo state that `sdd-verify` MUST check after implementation. All scenarios are evaluated against a fresh clone of the repo.

## ADDED Requirements

### Requirement: Required Root Files Present

The repository root MUST contain `LICENSE`, `README.md`, `.gitignore`, `.env.example`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `package.json`.

#### Scenario: All required files exist at root

- GIVEN a fresh clone of the repository
- WHEN listing the repo root
- THEN every file above is present and tracked by git
- AND none are empty (each has non-zero size)

### Requirement: Apache-2.0 License Compliance

`LICENSE` MUST contain the verbatim Apache-2.0 boilerplate. `package.json` MUST declare `"license": "Apache-2.0"`. `README.md` MUST reference Apache-2.0.

#### Scenario: License is Apache-2.0 across the repo

- GIVEN the repo root
- WHEN comparing `LICENSE` against the canonical Apache-2.0 text from apache.org
- THEN it matches verbatim
- AND `package.json` `license` field equals `"Apache-2.0"`
- AND `README.md` contains the string "Apache-2.0"

### Requirement: Environment Variable Contract

`.env.example` MUST include placeholder entries for every locked-stack secret with an inline comment explaining each. Required keys: `OPENAI_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `FLY_API_TOKEN`. No real secrets MAY be committed.

#### Scenario: Every required env var has a placeholder and a comment

- GIVEN `.env.example`
- WHEN parsing the file line by line
- THEN every required key above appears exactly once with a placeholder value
- AND every key has an adjacent comment line explaining its purpose
- AND no value resembles a real secret (e.g. starts with `sk-`, `pk_live_`, or has length > 20 alphanumerics)

### Requirement: Gitignore Coverage

`.gitignore` MUST ignore `.env`, `.env.local`, `node_modules/`, `__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `.next/`, `.DS_Store`, `*.sqlite`, `*.db`. It SHOULD include common IDE patterns (`.idea/`, `.vscode/`).

#### Scenario: Gitignore covers required patterns

- GIVEN `.gitignore`
- WHEN searching for each required pattern
- THEN every required pattern is present on its own line
- AND IDE patterns are present (warning only if missing, not failure)

### Requirement: Directory Skeleton With .gitkeep Markers

The directories `apps/web/`, `apps/api/`, `packages/ontology/`, `data/seed/`, and `data/scripts/` MUST exist and each MUST contain a tracked `.gitkeep` file so git preserves the empty directory.

#### Scenario: Skeleton directories are tracked

- GIVEN a fresh clone
- WHEN listing each directory above
- THEN each directory exists
- AND each contains a `.gitkeep` file tracked by git
- AND no other files are present in those directories

### Requirement: Workspace Declaration Without Runtime Dependencies

Root `package.json` MUST be a private package declaring pnpm workspaces (`"workspaces": ["apps/*", "packages/*"]` in `package.json` or equivalent in `pnpm-workspace.yaml`) and MUST NOT declare any runtime `dependencies` or `devDependencies`. It MUST pin `packageManager`.

#### Scenario: Workspace config is present and dependency-free

- GIVEN root `package.json`
- WHEN parsing it as JSON
- THEN `private` is `true`
- AND workspace globs `apps/*` and `packages/*` are declared (in `package.json` or `pnpm-workspace.yaml`)
- AND `packageManager` is set to a pinned pnpm version
- AND `dependencies` and `devDependencies` are absent or empty

### Requirement: README Content Structure

`README.md` MUST contain a one-paragraph project description, a "Stack" section listing the locked stack (Next.js 15, FastAPI, LangGraph, Neon Postgres + pgvector, Upstash Redis, Cloudflare R2, Clerk, OpenAI, Vercel + Fly.io), a "Status" section identifying Phase 0a (skeleton only), and a "Setup" placeholder pointing to a future phase.

#### Scenario: README sections are present

- GIVEN `README.md`
- WHEN searching for the section headings
- THEN headings "Stack", "Status", and "Setup" each appear exactly once
- AND the Status section explicitly mentions "Phase 0a"
- AND the Setup section is a placeholder (not real instructions)

### Requirement: Agent Guidance Files Reference SDD

`CLAUDE.md` and `AGENTS.md` MUST each reference `.atl/skill-registry.md`, `~/.claude/rules/sdd-orchestration.md`, and the SDD pipeline. `AGENTS.md` SHOULD note it is the broader-ecosystem mirror of `CLAUDE.md`.

#### Scenario: Both guidance files reference SDD machinery

- GIVEN `CLAUDE.md` and `AGENTS.md`
- WHEN searching each file
- THEN both contain the strings `.atl/skill-registry.md` and `sdd-orchestration.md`
- AND both describe or list the SDD pipeline phases
- AND `AGENTS.md` notes its mirror relationship with `CLAUDE.md`

### Requirement: Contribution and Security Channels

`CONTRIBUTING.md` MUST describe the SDD workflow (changes flow through `openspec/changes/`) and state that contributions are licensed under Apache-2.0. `SECURITY.md` MUST provide a vulnerability reporting channel (email or a TBD note).

#### Scenario: Contribution and security policies exist

- GIVEN `CONTRIBUTING.md` and `SECURITY.md`
- WHEN reading each file
- THEN `CONTRIBUTING.md` mentions `openspec/changes/` and "Apache-2.0"
- AND `SECURITY.md` provides a reporting channel (email pattern or explicit `TBD` placeholder)

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

### Requirement: OpenSpec Config Reflects Locked Decisions

`openspec/config.yaml` `context:` block MUST state license as Apache-2.0, MUST clarify hosting as "pay-as-you-go Fly.io, scale-to-zero" (replacing the prior TBD/free-tier wording), AND MUST describe the web stack as "Next.js 16 + Tailwind v4 + shadcn" and the API agent layer as "LangGraph 1.x". The redundant `Hosting:` line carried over from 0a SHOULD be collapsed so the hosting clause appears exactly once.

(Previously: required Apache-2.0 + pay-as-you-go/scale-to-zero phrasing. 0b additionally requires the Next.js 16 + Tailwind v4 + shadcn descriptor, the LangGraph 1.x note, and removal of the duplicated hosting line.)

#### Scenario: Config context updated for 0b stack

- GIVEN `openspec/config.yaml`
- WHEN reading the `context:` block
- THEN it contains "Apache-2.0"
- AND it contains "pay-as-you-go" and "scale-to-zero" (or equivalent phrasing) exactly once
- AND it contains the string "Next.js 16 + Tailwind v4 + shadcn"
- AND it contains the string "LangGraph 1.x"
- AND it no longer says license is TBD
