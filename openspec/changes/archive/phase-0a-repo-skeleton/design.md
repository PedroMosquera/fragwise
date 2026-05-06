# Design: Phase 0a — Repo Skeleton

## Technical Approach

Phase 0a has no runtime behavior. "Design" here means **concrete file content templates** that `sdd-apply` can paste verbatim. Every requirement in `specs/repo-skeleton/spec.md` maps to one or more templates below. No code is executed in this phase — `pnpm install` is deliberately deferred to phase-0b.

Conventions used in templates:
- `{{PLACEHOLDER}}` = literal token implementer should leave as-is unless the section says otherwise.
- `# comment` lines in shell-style files are mandatory; the spec's `Environment Variable Contract` requirement asserts each env var has an adjacent comment.

Library version pins were verified against the npm registry on the design date: **pnpm 10.33.3** is the current stable release (Context7 docs reference the 10.x line; npm `pnpm@latest` resolves to `10.33.3`).

## Architecture Decisions

### ADR-0001: License = Apache-2.0

- **Status**: Accepted
- **Context**: Fragwise will be open-sourced. The two realistic candidates were AGPLv3 (strong copyleft, blocks closed-source SaaS clones) and Apache-2.0 (permissive, includes patent grant). User explicitly chose Apache-2.0 in exploration U1 to maximize adoption and accept the trade-off that a commercial fork is legally permitted.
- **Decision**: Apache-2.0, verbatim text from `https://www.apache.org/licenses/LICENSE-2.0.txt`. No modifications to the boilerplate.
- **Consequences**: Permissive inbound = outbound; contributors implicitly grant patent rights. SaaS competitors are legally allowed; differentiation must come from execution, not license.

### ADR-0002: Monorepo via pnpm Workspaces

- **Status**: Accepted
- **Context**: Three viable layouts: (a) split repos per app, (b) Turborepo, (c) bare pnpm workspaces. The Python `apps/api` does not benefit from Turborepo's task graph since it has its own toolchain; pnpm's strict, deduplicated `node_modules` is the cheapest workable choice.
- **Decision**: Bare pnpm workspaces. Root `package.json` declares `workspaces: ["apps/*", "packages/*"]` for npm-tool compatibility; `pnpm-workspace.yaml` is the canonical declaration. `packageManager` pinned to `pnpm@10.33.3`.
- **Consequences**: Reversible via `rm pnpm-lock.yaml && edit package.json`. Future Turborepo adoption is additive (a `turbo.json` plus a devDependency).

### ADR-0003: Self-Hostable, Production via Fly.io Pay-as-you-go Scale-to-Zero

- **Status**: Accepted
- **Context**: Free tier was reconsidered after Fly.io retired its always-free allotment. The user accepted a small recurring cost in exchange for predictable production and zero throttling.
- **Decision**: Production hosting on Fly.io with scale-to-zero machines (idle cost ≈ $0). Self-hosting via `docker-compose.yml` (delivered phase-0b) remains a first-class path. `openspec/config.yaml` `context:` block is updated to reflect this.
- **Consequences**: Hosting cost is bounded but non-zero. Cold-start latency on first request after idle — acceptable for a chatbot.

### ADR-0004: CLAUDE.md and AGENTS.md Duplicated, Not Symlinked

- **Status**: Accepted
- **Context**: AGENTS.md is the broader-ecosystem standard (Cursor, Aider, Codex, Continue read it). CLAUDE.md is Anthropic's convention. Symlinks fragment on Windows checkouts and confuse some Git GUIs.
- **Decision**: Two physical files with identical content plus a one-line "keep in sync with the other" reminder.
- **Consequences**: Drift risk is real but cheap to detect — `sdd-verify` can diff them in any later phase.

## Data Flow

Not applicable — no runtime data flow. The "flow" of this change is purely build-time:

    sdd-apply ──→ writes 11 root files
                  writes 5 `.gitkeep` markers
                  edits openspec/config.yaml
                       │
                       └──→ sdd-verify checks every spec scenario

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `LICENSE` | Create | Verbatim Apache-2.0 text |
| `README.md` | Create | Project pitch + Status/Stack/Setup/License sections |
| `.gitignore` | Create | Python, Node, build outputs, env, OS, IDE patterns |
| `.env.example` | Create | All locked-stack secrets with inline comments, no real values |
| `CLAUDE.md` | Create | Anthropic agent guidance |
| `AGENTS.md` | Create | Same content as CLAUDE.md, ecosystem-framed |
| `CONTRIBUTING.md` | Create | SDD pipeline, licensing, PR flow |
| `SECURITY.md` | Create | Reporting channel + 90-day disclosure |
| `package.json` | Create | Private workspace root, no deps, packageManager pinned |
| `pnpm-workspace.yaml` | Create | Canonical pnpm workspace declaration |
| `apps/web/.gitkeep` | Create | Empty marker |
| `apps/api/.gitkeep` | Create | Empty marker |
| `packages/ontology/.gitkeep` | Create | Empty marker |
| `data/seed/.gitkeep` | Create | Empty marker |
| `data/scripts/.gitkeep` | Create | Empty marker |
| `openspec/config.yaml` | Modify | Update `context:` block — license + hosting |

## File Templates

### 1. `LICENSE`

Use the canonical Apache-2.0 text from `https://www.apache.org/licenses/LICENSE-2.0.txt` verbatim. **No modifications** — do not insert a copyright header or change line endings beyond what apache.org publishes. The implementer should `curl` the file or paste from the canonical source.

Implementation note for `sdd-apply`:

```bash
curl -fsSL https://www.apache.org/licenses/LICENSE-2.0.txt -o LICENSE
```

### 2. `README.md`

```markdown
# Fragwise

Fragwise is an open-source fragrance discovery platform with a built-in AI chatbot guide. It serves connoisseurs cataloging notes, accords, and houses, and beginners who just want to find a scent they will love. Project URL (once deployed): https://fragwise.app

## Status

**Phase 0a — repo skeleton only.** This repository currently contains structural and legal scaffolding. There is no runnable code yet. Application code, tooling, and the data model arrive in phases 0b and 0c.

## Stack

- Web: Next.js 15 + Tailwind CSS + shadcn/ui
- API: Python FastAPI + LangGraph
- Database: Neon Postgres + pgvector
- Cache / rate limit: Upstash Redis
- Object storage: Cloudflare R2
- Auth: Clerk
- LLM: OpenAI
- Hosting: Vercel (web) + Fly.io (api), pay-as-you-go with scale-to-zero
- Self-hostable via `docker-compose` (delivered in phase 0b)

## Setup

Local setup instructions arrive in **phase 0b** along with `docker-compose.yml`, the dev `justfile`, and lint/type configs. Until then, this repo is not runnable.

## License

Licensed under [Apache-2.0](./LICENSE). Inbound contributions are licensed outbound under the same terms; see [CONTRIBUTING.md](./CONTRIBUTING.md).
```

### 3. `.gitignore`

```gitignore
# --- Python ---
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
env/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/

# --- Node / JS ---
node_modules/
.pnpm-store/
.npm/
.yarn/

# --- Build outputs ---
dist/
build/
.next/
out/
*.tsbuildinfo

# --- Env / secrets ---
.env
.env.local
.env.*.local

# --- Databases / artifacts ---
*.sqlite
*.sqlite3
*.db

# --- OS ---
.DS_Store
Thumbs.db

# --- IDE ---
.vscode/
.idea/
*.swp
*.swo
```

### 4. `.env.example`

```dotenv
# === OpenAI ===
# API key for chat + embeddings. Get from https://platform.openai.com/api-keys
OPENAI_API_KEY=your-openai-api-key-here

# === Neon Postgres + pgvector ===
# Connection string for the catalog DB. Get from https://console.neon.tech (free tier).
# Format: postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# === Upstash Redis (cache + rate limit) ===
# REST or rediss:// URL. Get from https://console.upstash.com (free tier).
REDIS_URL=rediss://default:password@host:6379

# === Cloudflare R2 (image storage) ===
# Account ID from the Cloudflare dashboard sidebar.
R2_ACCOUNT_ID=your-r2-account-id
# API token credentials — create under R2 > Manage R2 API Tokens.
R2_ACCESS_KEY_ID=your-r2-access-key-id
R2_SECRET_ACCESS_KEY=your-r2-secret-access-key
# Bucket name created in the R2 dashboard.
R2_BUCKET=fragwise-images

# === Clerk (auth) ===
# Publishable key (safe for client). Get from https://dashboard.clerk.com > API Keys.
CLERK_PUBLISHABLE_KEY=pk_test_replace_me
# Secret key (server-only). Same dashboard page.
CLERK_SECRET_KEY=sk_test_replace_me

# === Fly.io (deployment) ===
# Personal access token. Generate via `fly auth token` after `fly auth login`.
FLY_API_TOKEN=your-fly-api-token
```

Note: spec scenario forbids real-secret-shaped values. The placeholders above stay safely under the 20-char-alphanumeric guard and use clearly-fake tokens (`pk_test_replace_me`, `your-...`).

### 5. `CLAUDE.md`

```markdown
# Fragwise — Claude Agent Guide

Fragwise is an open-source fragrance discovery platform with an AI chatbot guide for both beginners and connoisseurs. This file orients Anthropic-family agents (Claude Code, Claude.ai) to the project's conventions.

> Keep this file in sync with `AGENTS.md` (the broader-ecosystem mirror). If you edit one, edit both.

## Stack Summary

- Web: Next.js 15 + Tailwind + shadcn/ui (`apps/web`)
- API: FastAPI + LangGraph in Python (`apps/api`)
- Ontology: shared notes/accords taxonomy (`packages/ontology`)
- Data: Neon Postgres + pgvector, Upstash Redis, Cloudflare R2
- Auth: Clerk. LLM: OpenAI. Hosting: Vercel + Fly.io (pay-as-you-go, scale-to-zero).

## Monorepo Layout

```
apps/web/              # Next.js frontend
apps/api/              # FastAPI backend
packages/ontology/     # Shared taxonomy package
data/seed/             # Seed datasets
data/scripts/          # Ingestion + maintenance scripts
openspec/              # SDD specs and changes
```

## Workflow: Spec-Driven Development (SDD)

This project uses the SDD pipeline from `~/.claude/rules/sdd-orchestration.md`. **Do not edit production files directly for non-trivial work** — drive every change through:

1. `sdd-explore` — investigate
2. `sdd-propose` — write proposal
3. `sdd-spec` — write delta specs (Given/When/Then, RFC 2119)
4. `sdd-design` — technical design + ADRs
5. `sdd-tasks` — implementation checklist
6. `sdd-apply` — implement
7. `sdd-verify` — validate against specs
8. `sdd-archive` — sync deltas to main specs

Skill registry: see `.atl/skill-registry.md` for project-specific compact rules and skill loadout. Always consult this file when picking skills.

## Conventions

| Area | Tool | Notes |
|------|------|-------|
| Python lint | `ruff` | Configured in phase-0b |
| Python types | `mypy` | Strict mode in `apps/api` |
| TS lint | `eslint` | Next.js preset + repo overrides |
| TS types | `tsc --noEmit` | Run in CI |
| Library docs | Context7 MCP | Use `resolve-library-id` then `query-docs` before writing code that touches a third-party library |
| Commits | Minimal, no co-authored trailers | Per user preference |

## Do Not

- Do **not** bypass SDD for non-trivial changes (>~50 LOC or multiple files).
- Do **not** commit `.env` or any real secret. `.env.example` is the contract.
- Do **not** add dependencies without an `sdd-propose` step justifying the addition.
- Do **not** symlink `CLAUDE.md` and `AGENTS.md` — keep them as separate files.
- Do **not** modify the `LICENSE` file. Apache-2.0 verbatim only.
```

### 6. `AGENTS.md`

`AGENTS.md` is the cross-agent ecosystem standard (Cursor, Aider, Codex, Continue, etc.) and mirrors `CLAUDE.md` content with framing tweaks.

```markdown
# Fragwise — Agent Guide (AGENTS.md)

This is the ecosystem-standard agent guide for Fragwise, mirroring `CLAUDE.md`. Tools that read `AGENTS.md` (Cursor, Aider, Codex, Continue, Cline, etc.) should treat this file as authoritative.

> Keep this file in sync with `CLAUDE.md`. If you edit one, edit both.

## Project Pitch

Fragwise is an open-source fragrance discovery platform with an AI chatbot guide. It serves both connoisseurs (notes, accords, houses) and beginners (natural-language scent discovery).

## Stack Summary

- Web: Next.js 15 + Tailwind + shadcn/ui (`apps/web`)
- API: FastAPI + LangGraph in Python (`apps/api`)
- Ontology package: `packages/ontology`
- Data: Neon Postgres + pgvector, Upstash Redis, Cloudflare R2
- Auth: Clerk. LLM: OpenAI. Hosting: Vercel + Fly.io (pay-as-you-go, scale-to-zero).

## Monorepo Layout

```
apps/web/              # Next.js frontend
apps/api/              # FastAPI backend
packages/ontology/     # Shared taxonomy
data/seed/             # Seed datasets
data/scripts/          # Ingestion + maintenance scripts
openspec/              # SDD specs and changes
```

## Workflow: Spec-Driven Development

Fragwise uses the SDD pipeline (see `~/.claude/rules/sdd-orchestration.md`). All non-trivial work flows through:

`sdd-explore` -> `sdd-propose` -> `sdd-spec` -> `sdd-design` -> `sdd-tasks` -> `sdd-apply` -> `sdd-verify` -> `sdd-archive`

Project skill registry and compact rules live at `.atl/skill-registry.md`.

## Conventions

| Area | Tool |
|------|------|
| Python lint | ruff |
| Python types | mypy |
| TypeScript lint | eslint |
| TypeScript types | tsc --noEmit |
| Library docs | Context7 MCP (resolve-library-id then query-docs) |

## Do Not

- Do not bypass SDD for non-trivial changes.
- Do not commit `.env` or real secrets — `.env.example` is the contract.
- Do not add dependencies without a proposal.
- Do not symlink this file with `CLAUDE.md`.
- Do not modify `LICENSE`.
```

### 7. `CONTRIBUTING.md`

```markdown
# Contributing to Fragwise

Thanks for considering a contribution. Fragwise is open-source under [Apache-2.0](./LICENSE), and the project follows a strict spec-driven development workflow.

## How to Propose a Change

All non-trivial changes flow through the SDD pipeline rooted at `openspec/changes/`. The lifecycle:

1. **Explore** — investigate the idea (`openspec/changes/{name}/exploration.md`).
2. **Propose** — write `proposal.md`: intent, scope, approach, rollback.
3. **Spec** — add delta specs under `openspec/changes/{name}/specs/{domain}/spec.md` using Given/When/Then with RFC 2119 keywords.
4. **Design** — `design.md` with ADRs and concrete file changes.
5. **Tasks** — `tasks.md` checklist.
6. **Apply** — implement, ticking tasks as they land.
7. **Verify** — `verify-report.md` validates each spec scenario.
8. **Archive** — merge deltas into `openspec/specs/` and move the change to `openspec/changes/archive/YYYY-MM-DD-{name}/`.

If you are using Claude Code or another agent, the `sdd-*` skills automate each step. Otherwise, follow the same artifact layout manually.

## How to Run Locally

Local development tooling (Docker Compose, justfile, lint configs) is delivered in **phase 0b**. Until that change lands, the repo is intentionally not runnable.

## Code Style

Tooling specifics (`ruff`, `mypy`, `eslint`, `prettier`, `tsc`) are pinned in **phase 0b**. Once they land, every PR must pass lint, type, and test gates.

## Licensing (Inbound = Outbound)

By submitting a contribution you agree your code is licensed under [Apache-2.0](./LICENSE), the same license as the project. No CLA is required.

## Pull Request Process

1. Open the PR against `main`.
2. Reference the `openspec/changes/{name}/` directory in the PR description.
3. Make sure `sdd-verify` passes (or a manual checklist substitute, pre-0b).
4. Squash-merge once a maintainer approves.
```

### 8. `SECURITY.md`

```markdown
# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Fragwise, please **do not open a public GitHub issue**. Report it privately to:

> `security@fragwise.app` (TBD — pending domain ownership; until then, contact the maintainer via the email listed on the GitHub profile of the repository owner)

Include:
- A description of the vulnerability
- Steps to reproduce
- Affected component (`apps/web`, `apps/api`, `packages/ontology`, etc.)
- Your assessment of impact

## Disclosure Policy

Fragwise follows a **90-day responsible disclosure** policy:

1. Acknowledgement of your report within 5 business days.
2. A patch or mitigation will be developed in private.
3. Public disclosure occurs after a fix is released, or 90 days after initial report — whichever comes first.

## Supported Versions

Until Fragwise reaches a tagged 1.0, only the `main` branch is supported. Once releases begin, this section will list supported tags.
```

### 9. `package.json`

```json
{
  "name": "fragwise",
  "version": "0.0.0",
  "private": true,
  "description": "Open-source fragrance discovery platform with an AI chatbot guide.",
  "license": "Apache-2.0",
  "workspaces": [
    "apps/*",
    "packages/*"
  ],
  "packageManager": "pnpm@10.33.3"
}
```

Notes:
- `private: true` is required by the spec.
- `workspaces` is included for npm-tool compatibility; the canonical declaration is `pnpm-workspace.yaml` (item 10).
- No `dependencies` or `devDependencies` keys — spec forbids them in phase 0a.
- `packageManager` pin is **pnpm@10.33.3**, verified against the npm registry on 2026-05-06.

### 10. `pnpm-workspace.yaml`

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

### 11. `.gitkeep` Markers

Each file is a zero-byte tracked file at the listed path. No content — its only purpose is to let git track the empty directory.

| Path | Content |
|------|---------|
| `apps/web/.gitkeep` | (empty) |
| `apps/api/.gitkeep` | (empty) |
| `packages/ontology/.gitkeep` | (empty) |
| `data/seed/.gitkeep` | (empty) |
| `data/scripts/.gitkeep` | (empty) |

### 12. `openspec/config.yaml` — `context:` Block Update

Replace the existing `context:` block with the version below. Only the `context:` literal-block scalar changes; `schema`, `rules`, `testing`, etc. stay as-is.

**Diff (intent):**

```diff
 context: |
   Fragwise: open-source fragrance discovery + database with AI chatbot guide.
   Monorepo: apps/web (Next.js 15 + Tailwind + shadcn), apps/api (Python FastAPI + LangGraph),
   packages/ontology (notes/accords taxonomy), data/ (seed datasets and ingestion scripts).
   Data: Neon Postgres + pgvector (catalog and embeddings), Upstash Redis (cache + rate limit),
   Cloudflare R2 (images). Auth: Clerk. LLM: OpenAI. Hosting: Vercel + Fly.io. All free tier.
-  Self-hostable via docker-compose. License: TBD (likely AGPLv3 or MIT).
+  Self-hostable via docker-compose.
+  License: Apache-2.0.
+  Hosting: Vercel (web) + Fly.io (api) on pay-as-you-go, scale-to-zero machines.
```

The two new lines satisfy the "Apache-2.0" string check and the "pay-as-you-go" + "scale-to-zero" string checks from the `OpenSpec Config Reflects Locked Decisions` requirement, and remove the prior `License: TBD` wording.

## Interfaces / Contracts

No runtime interfaces. The only "contracts" introduced are:

1. **Env-var contract** (`.env.example`) — the canonical list of secrets every later phase may consume.
2. **Workspace globs** (`pnpm-workspace.yaml`) — the canonical set of locations app/package code may live in.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | n/a | No code in phase 0a |
| Integration | n/a | No services in phase 0a |
| E2E | n/a | No app yet |
| Repo invariants | Every spec scenario | `sdd-verify` runs shell + grep checks against the working tree (file existence, regex matches, JSON parse, license byte-equality vs apache.org canonical text) |

`sdd-verify` should treat each spec scenario as a discrete check returning pass/fail with the failed-line excerpt for grep-style checks.

## Migration / Rollout

No migration. Rollback = `git revert` of the merge commit. No external state, no DB, no DNS, no cloud accounts touched.

## Open Questions

- [ ] **Security email**: `SECURITY.md` lists `security@fragwise.app` as TBD. Confirm the domain is owned and an alias exists before phase 0a is archived; otherwise replace with the maintainer's GitHub-listed contact.

That is the only open question. All other decisions are resolved.
