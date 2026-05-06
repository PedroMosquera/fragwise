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

### Requirement: No Application Code Or Build Tooling

The repository MUST NOT contain any `*.ts`, `*.tsx`, `*.py`, `*.sql`, `Dockerfile`, `docker-compose.yml`, `justfile`, `Makefile`, or `.github/workflows/*.yml` files. These belong to phase 0b/0c.

#### Scenario: Forbidden file types are absent

- GIVEN a fresh clone
- WHEN running `git ls-files` against the forbidden patterns
- THEN the result is empty for every pattern
- AND no `.github/workflows/` directory exists

### Requirement: OpenSpec Config Reflects Locked Decisions

`openspec/config.yaml` `context:` block MUST state license as Apache-2.0 and clarify hosting as "pay-as-you-go Fly.io, scale-to-zero" (replacing the prior TBD/free-tier wording).

#### Scenario: Config context updated

- GIVEN `openspec/config.yaml`
- WHEN reading the `context:` block
- THEN it contains "Apache-2.0"
- AND it contains "pay-as-you-go" and "scale-to-zero" (or equivalent phrasing)
- AND it no longer says license is TBD
