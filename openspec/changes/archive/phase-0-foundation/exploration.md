# Exploration: phase-0-foundation

Investigation of the foundational scaffolding for Fragwise (monorepo, dev tooling, Docker compose, ontology format, DB schema v1, CI). No code exists yet — repo holds only `.git/`, `openspec/`, and `.atl/skill-registry.md`. This document surfaces unknowns, risks, trade-offs, and a recommendation on whether Phase 0 should be split.

## Current State

- Repo `/Users/alexmosquera/workspace/fragwise/` is empty of source code.
- `openspec/config.yaml` already records the intended stack (Next.js 15, FastAPI + LangGraph, Neon Postgres + pgvector, Upstash Redis, R2, Vercel + Fly.io, Clerk) and explicitly marks license as "TBD (likely AGPLv3 or MIT)".
- Skill registry at `.atl/skill-registry.md` notes "No project-level CLAUDE.md / AGENTS.md / .cursorrules yet. To be added in Phase 0."
- No CI, no tests, no migrations, no Docker.

## Affected Areas

This change creates new files only — nothing to refactor. The footprint is:

- Repo root — `.gitignore`, `.env.example`, `README.md`, `LICENSE`, `docker-compose.yml`, task runner config, root `package.json` (if a JS workspace manager is used), `.editorconfig`, GitHub Actions under `.github/workflows/`.
- `apps/web/` — Next.js 15 App Router skeleton, `package.json`, `tsconfig.json`, `tailwind.config.ts`, `eslint.config.mjs`, `vitest.config.ts`, `.prettierrc`, shadcn init artifacts.
- `apps/api/` — FastAPI skeleton, `pyproject.toml`, `ruff.toml` (or pyproject section), `mypy` config, `pytest` config, `Dockerfile`, Alembic env, `app/` package.
- `packages/ontology/` — schema definitions for note hierarchy, accord families, synonyms (format only, no data).
- `data/seed/`, `data/scripts/` — empty stubs with READMEs explaining future use.
- DB schema v1 — Alembic revision (or raw SQL) creating `fragrances`, `notes`, `accords`, `brands`, `perfumers`, `articles`, `fragrance_notes`, `fragrance_embeddings`.
- `openspec/specs/` — populated with foundation domain specs after `sdd-archive`.

## Key Unknowns (decisions the user must make before sdd-propose)

### U1. License: MIT vs Apache-2.0 vs AGPLv3
The project is OSS and self-hostable. License choice is permanent and load-bearing for community contributions and copy-cat protection.
- **MIT** — maximum adoption, no copyleft. Anyone can fork and run a closed SaaS competitor.
- **Apache-2.0** — like MIT plus explicit patent grant and contribution clauses. Slightly more enterprise-friendly. Still permissive (no copyleft).
- **AGPLv3** — strong copyleft; if anyone runs a modified version as a network service they must publish their changes. Strongest defense against a closed-source SaaS clone but scares some contributors and disqualifies certain corporate users.
- Recommendation: **Apache-2.0** as the default — it gives you patent protection that MIT lacks, is the modern standard for new OSS, and keeps contribution friction low. Pick **AGPLv3** only if "no closed-source clone of Fragwise" is a stated goal. Avoid plain MIT unless you specifically want zero patent clauses.

### U2. Hosting: Fly.io free tier is gone for new accounts (2026)
Verified via fly.io/docs/about/pricing/: **Fly.io no longer accepts new free tier signups in 2026.** The locked-stack assumption "Fly.io free tier" is invalid for a fresh OSS project. Options:
- **Pay-as-you-go Fly.io** — ~$2-6/month minimum for shared-cpu-1x with 256MB-1GB. Realistic for FastAPI + LangGraph + sentence-transformers (which alone needs ~500MB-1GB). Not free, but cheap.
- **Render free tier** — has a free web-service tier with sleep-after-15-min-idle and 512MB RAM. Likely too small for sentence-transformers and cold starts hurt the chatbot UX.
- **Railway / Koyeb / Northflank free tiers** — small RAM ceilings (256-512MB), generally too tight for ML deps.
- **Hugging Face Spaces (Docker)** — free 16GB RAM 2vCPU CPU spaces, designed for ML, but tied to HF auth and not a great primary API host.
- **Self-hosted on a $5 VPS (Hetzner CX22, DigitalOcean basic)** — guaranteed RAM, full control, requires ops work.
- Recommendation: **Drop "free tier" as a hard constraint for the API.** Choose pay-as-you-go Fly.io OR a $5 VPS as the documented production target, and keep self-hosting via Docker Compose as the OSS-friendly story. Update `openspec/config.yaml`'s context block accordingly.

### U3. Embedding strategy: sentence-transformers in-process vs OpenAI embeddings API
The brief says "sentence-transformers" implicitly (semantic cache, ranking) but also "LLM via OpenAI." Two paths:
- **In-process sentence-transformers** (e.g., `all-MiniLM-L6-v2`, 384-dim, ~80MB model) — free per-query, but adds ~300-500MB resident memory + first-load latency to the API container. Forces vector dim choice now.
- **OpenAI `text-embedding-3-small`** (1536-dim, can be reduced via `dimensions` parameter to 256/512) — paid per token (~$0.02/1M tokens, very cheap), zero memory footprint, no model download in CI/Docker, but requires API key for every embed call (no offline dev).
- This decision drives: vector column dimension in `fragrance_embeddings`, Docker image size, Fly.io memory tier, semantic-cache implementation, dev-onboarding (whether `OPENAI_API_KEY` is mandatory to run locally).
- Recommendation: **OpenAI `text-embedding-3-small` with `dimensions=512`** for v1. Saves ~600MB of container memory, removes the GPU/CPU model-load complexity, and the cost is trivial at expected catalog size. Offer sentence-transformers as a pluggable provider in a later phase if cost or offline-dev becomes a concern.

### U4. Migration tool: Alembic vs raw SQL vs sqitch vs Drizzle Kit
- **Alembic** — Python-native, integrates with SQLAlchemy models if you adopt them. Autogenerate is excellent for normal schema but **does not detect pgvector index types or extensions** — those need raw `op.execute()` blocks. Mature, well-known.
- **Raw SQL files + a tiny runner** (e.g., `dbmate`, `goose`, or a homemade script) — language-agnostic, zero coupling to ORM, easy to read in PR review. Loses autogenerate.
- **sqitch** — Perl-based, robust, dependency-graph-aware. Extra runtime dep most contributors don't have.
- **Drizzle Kit** (TS-first) — beautiful DX but the API server is Python; running migrations from Node feels wrong.
- Recommendation: **Alembic with hand-written initial revision** (no autogenerate yet). Use `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` and raw `CREATE INDEX ... USING hnsw ...` for pgvector indexes. This gives migration history + dev/prod parity without coupling to SQLAlchemy declarative models on day 1. (Per Context7 Alembic docs, replaceable-object and `op.execute` are the standard escape hatches.)

### U5. Monorepo manager: pnpm workspaces vs npm workspaces vs Turborepo vs no manager
- **No manager** — apps/web is the only Node app; apps/api is Python. There is no shared TS code yet. A monorepo manager is overkill on day 1.
- **npm workspaces** — built into npm, zero install, supports `apps/web` + future `packages/ui` cleanly.
- **pnpm workspaces** — faster, stricter hoisting, common in Vercel projects.
- **Turborepo** — adds task graph caching; only pays off when you have ≥3 Node packages with build steps.
- Recommendation: **pnpm workspaces** for forward-compatibility (cheap to add now, painful to retrofit when `packages/ui` and `packages/types` arrive). Skip Turborepo until task-graph caching matters.

### U6. Task runner: Make vs justfile vs npm scripts vs taskfile
- **Make** — universal, but tab-vs-space footguns and weird shell semantics.
- **justfile** — modern, friendlier syntax, but contributors have to install `just`.
- **Taskfile (go-task)** — YAML-based, cross-platform, single binary.
- **npm scripts at the root** — works only if you adopt a Node workspace manager; awkward to invoke Python tooling.
- Recommendation: **justfile** — it's the modern default in OSS Python+TS hybrid projects, handles `apps/api` and `apps/web` symmetrically, and a one-liner README install (`brew install just`) is acceptable friction. Add a `Makefile` shim only if you get explicit user pushback.

### U7. Ontology file format: YAML vs JSON vs TOML
- **YAML** — most readable for nested taxonomy data, comments allowed, but parser footguns (e.g., the Norway problem) and indentation pain.
- **JSON / JSON5** — universal, but no comments in plain JSON.
- **TOML** — flat-friendly, less ergonomic for deep hierarchies like note trees.
- Recommendation: **YAML** for note hierarchy and accord families (deep nested), **JSON** for synonyms (flat key→list maps, easier to lint and diff). Validate with JSON Schema or pydantic models in `packages/ontology/` so misformatted contributions fail CI.

### U8. CI: GitHub Actions structure
- Single monolithic workflow vs per-app workflows vs matrix.
- Recommendation: **Per-app workflows with path filters** (`apps/web/**` triggers web CI, `apps/api/**` triggers api CI), plus one repo-wide workflow for things like `gitleaks` / `actionlint`. Avoid matrix on day 1 — it adds debugging difficulty without payoff at this size.

### U9. Python packaging: poetry vs uv vs pip-tools vs hatch
- **uv** is now the de facto default for new Python projects in 2026: fastest installer, replaces pip + virtualenv + pip-tools, integrates with pyproject. Recommended.
- Poetry still works but is being eclipsed.
- pip-tools is too low-level for a fresh project.
- Recommendation: **uv** with a `pyproject.toml` and `uv.lock`. Saves substantial CI time and contributor onboarding pain.

### U10. Local dev DB: Postgres in docker-compose or hosted Neon branch
The brief says docker-compose for self-hosting. Two questions for local dev:
- Does the repo's docker-compose ship a Postgres image **with pgvector pre-installed** (e.g., `pgvector/pgvector:pg16`) or vanilla Postgres + a SQL bootstrap?
- Does CI use a Postgres service container, or a Neon dev branch?
- Recommendation: Use the official **`pgvector/pgvector:pg16`** image for both docker-compose and CI services. Neon dev branches are great for staging but add a paid-account dependency to CI; keep them out of Phase 0.

## Risks

- **R1 — Stack assumption invalid**: Fly.io has no free tier for new accounts in 2026. Phase 0 README/docs will misrepresent the deploy path unless this is reconciled (see U2). High likelihood of confusing first contributors. **Mitigation**: pivot the documented production target to pay-as-you-go Fly.io or a self-hosted VPS, and keep docker-compose as the universal "just run it" story.
- **R2 — sentence-transformers footprint blows the chosen host**: even on a paid 1GB Fly Machine, transformers + torch CPU wheels can exceed 1GB image size and cause OOM at load. **Mitigation**: pick OpenAI embeddings (U3) and defer local-model support to a flagged provider abstraction.
- **R3 — pgvector index creation in Alembic is non-obvious**: autogenerate will not produce HNSW index DDL. New contributors who run autogenerate will silently lose those indexes. **Mitigation**: document the `op.execute` pattern in the initial migration's docstring and add a CI check that key indexes exist after migration.
- **R4 — License decision deferred**: shipping any code without a `LICENSE` file makes early external contributions legally murky (default copyright = all rights reserved). **Mitigation**: U1 must close before merge, even if the answer is provisional.
- **R5 — Schema v1 locks vector dimension before the embedding model is chosen**: changing dimension later requires a destructive migration on `fragrance_embeddings`. **Mitigation**: U3 must close before the migration is written.
- **R6 — CLAUDE.md / AGENTS.md missing**: skill-registry flags this as a Phase 0 deliverable, but the brief omits it. Without it, future agent runs lose project conventions. **Mitigation**: include both files in Phase 0 scope (lightweight, no real cost).
- **R7 — Phase 0 task count is large**: ~6 distinct tracks (monorepo, web tooling, api tooling, docker, ontology format, schema, CI) each with their own setup chores. As one change, `tasks.md` will balloon and `sdd-apply` runs become unwieldy.
- **R8 — Upstash Redis and R2 not in Phase 0 scope**: confirm. The brief lists them in the locked stack but Phase 0 deliverables don't mention them. If they are deferred, `.env.example` should still document the variables; if not, add a Phase 0 task.
- **R9 — Clerk postponement**: brief explicitly defers auth past Phase 0. Confirm `.env.example` should still have Clerk placeholders commented out so the contract is visible.

## Trade-offs Worth Surfacing

- **Self-hostable + free-tier hosted** is a tension. Self-hostable is OSS table stakes; "free-tier deployable" is a contributor-recruitment promise. Fly.io's policy change forces a choice: drop the free promise OR change the recommended host. The cheapest honest answer is "production deploys ~$5/month; local dev is free via docker-compose."
- **Alembic vs raw SQL**: Alembic gives history and replayability but introduces SQLAlchemy as a transitive opinion (you'll be tempted to use ORM models). Raw SQL keeps things explicit but adds a homemade runner. Alembic wins on day 1 for the migration history alone.
- **uv vs poetry**: poetry is more recognized, uv is faster and is winning. Picking uv is a small bet that pays off in CI minutes; if you hate it, switching pyproject backends later is mechanical.
- **Vector dimension**: 384 (sentence-transformers MiniLM) vs 512 (OpenAI 3-small reduced) vs 1536 (OpenAI default). Lower dim = faster index, smaller storage, slightly less recall. 512 is a good middle ground; 1536 is wasteful at v1 catalog size (probably <100K fragrances).

## Recommendation: Split Phase 0 into smaller changes

**Yes — Phase 0 as written is too broad to land cleanly.** Recommend splitting into 3 sequential changes, each independently shippable and reviewable:

1. **`phase-0a-repo-skeleton`** — Repo-root deliverables only: `.gitignore`, `LICENSE`, `README.md` (project pitch + setup steps), `.env.example` (with all stack vars commented and grouped), `.editorconfig`, monorepo manager init (pnpm workspaces), justfile, top-level directory stubs (`apps/`, `packages/`, `data/`) with placeholder READMEs, plus `CLAUDE.md` / `AGENTS.md` for agent context. Closes U1, U5, U6, R4, R6. No code, no Docker, no DB.

2. **`phase-0b-app-tooling-and-docker`** — Per-app dev tooling and local-dev infra: `apps/web` Next.js 15 + Tailwind + shadcn + vitest + eslint + prettier + tsc; `apps/api` FastAPI + uv + ruff + mypy + pytest + httpx + Dockerfile; `docker-compose.yml` running `pgvector/pgvector:pg16` and `redis:7`; first GitHub Actions workflow per app with path filters. Closes U8, U9, U10. Yields: `just dev` works, both apps boot, CI green on a no-op PR.

3. **`phase-0c-schema-and-ontology`** — Database schema v1 + ontology format: Alembic init, initial migration creating `fragrances`, `notes`, `accords`, `brands`, `perfumers`, `articles`, `fragrance_notes`, `fragrance_embeddings` (dimension chosen in U3); `packages/ontology/` schema files (note hierarchy YAML, accord families YAML, synonyms JSON) with pydantic validators; `data/seed/` and `data/scripts/` stubs; CI step that runs `alembic upgrade head` against the docker-compose DB and validates ontology files. Closes U3, U4, U7, R2, R3, R5.

This split keeps each `tasks.md` under ~15 items, each PR diff reviewable, and each phase's failure isolated. Phase 0a's deliverables (license, env contract, agent context) are also the cheapest insurance for everything that comes after.

## Ready for Proposal

**Partial.** The orchestrator should report back to the user with the 10 unknowns above (especially U1 license, U2 hosting, U3 embedding strategy, U4 migration tool — these block a sensible proposal) and the proposed 3-way split. Once those decisions land, `sdd-propose` can run against `phase-0a-repo-skeleton` first.
