# Proposal: Phase 0b — App Tooling and Docker

## Intent

Phase 0a left empty `apps/` and `packages/` with `.gitkeep` markers and forbids any code or tooling files. 0b makes the workspace executable: `apps/web` (Next.js 16 + Tailwind v4 + shadcn) and `apps/api` (FastAPI + LangGraph 1.x via uv) become real packages, local-dev infra (`docker-compose.yml`, `justfile`) lands at the root, and per-area CI workflows replace the current absence of GitHub Actions. No domain logic — just the toolchain that every later phase compiles against.

## Scope

### In Scope
- `apps/web/`: Next.js 16 App Router (TS, src/), Tailwind v4 (`@tailwindcss/postcss`, no JS config), shadcn primitives (button, card, input, label, dialog, sonner, dropdown-menu, tabs, separator, badge), eslint flat config, prettier, vitest + @testing-library/react, Playwright config + 1 smoke test (manual-trigger), home page rendering "Fragwise", theme provider scaffolded.
- `apps/api/`: FastAPI app factory + no-op lifespan, `/healthz` returning `{"status":"ok"}`, LangGraph 1.x stub StateGraph (no LangChain), uv single-project `pyproject.toml`, ruff + mypy strict + pytest + httpx.AsyncClient, one passing test, `apps/api/Dockerfile` (Fly.io path).
- Repo root: `docker-compose.yml` (`pgvector/pgvector:pg16`, `redis:7-alpine`, named volumes, dev ports), `justfile` (`install`, `dev`, `dev-web`, `dev-api`, `test*`, `lint*`, `db-up`, `db-down`, `db-shell`).
- `.github/workflows/`: `web.yml` (paths `apps/web/**` + root pnpm files), `api.yml` (paths `apps/api/**`), `openspec.yml` (any PR; bash proposal-presence check).
- `openspec/config.yaml` `context:` updated: "Next.js 16 + Tailwind v4 + shadcn"; LangGraph 1.x noted.

### Out of Scope
Storybook; next-intl/i18n; pre-commit framework hooks; Sentry/OpenTelemetry; domain logic / catalog data / agent orchestration / chatbot UI; DB migrations and ontology content (0c); design polish beyond default shadcn tokens.

## Capabilities

### New Capabilities
- `web-app`: Next.js 16 web shell, Tailwind v4 styling, shadcn primitive set, vitest + Playwright test infra, smoke home page.
- `api-app`: FastAPI service with `/healthz`, LangGraph stub, uv-managed deps, ruff/mypy/pytest, Dockerfile.
- `dev-infra`: docker-compose (postgres + redis), justfile orchestration recipes.
- `ci-pipeline`: per-area GitHub Actions workflows (web, api, openspec) with path filters and dependency caching.

### Modified Capabilities
- `repo-skeleton`: relax 0a's "no application code or build tooling" invariant — `apps/web/**`, `apps/api/**`, `docker-compose.yml`, `justfile`, `.github/workflows/**`, `Dockerfile` become permitted; config.yaml context line updated.

## Approach

Hand-roll `apps/web` (reject `create-next-app` and shadcn `--monorepo`; both write artifacts we'd have to audit — see exploration U-Web-1). Adopt FastAPI app-factory + no-op lifespan now to spare a 0c refactor (U-API-5/6). Pin LangGraph `~=1.0.8` and assert via `uv tree` that no torch/transformers leak in (A-R3). Pin `pgvector/pgvector:pg16` to mirror Neon, not pgvector head (I-R1). CI workflows pin actions to commit SHAs; cache via `setup-uv` + `setup-node cache: 'pnpm'` + Playwright cache (U-Infra-5). `just dev` uses `&` + `wait` (POSIX-only, documented).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/web/` | New | Next.js 16 + Tailwind v4 + shadcn + vitest + Playwright |
| `apps/api/` | New | FastAPI + LangGraph stub + uv + ruff/mypy/pytest + Dockerfile |
| `docker-compose.yml` | New | postgres (pg16) + redis services |
| `justfile` | New | dev orchestration recipes |
| `.github/workflows/` | New | web.yml, api.yml, openspec.yml |
| `openspec/config.yaml` | Modified | context block: Next.js 16, Tailwind v4, LangGraph 1.x |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| W-R1 Tailwind v4 monorepo content detection edge cases | Med | Keep all class-emitting code inside `apps/web/`; no `packages/ui` |
| A-R2 LangGraph 1.0 install churn | Med | Pin `~=1.0.8`; review migration notes pre-merge |
| A-R3 Heavy ML transitive deps creep in | Low | `uv tree` assertion in verify; pytest checks `import torch` raises ImportError |
| I-R1 pgvector tag drift vs Neon | Low | Doc comment in compose file explaining the pin rationale |
| I-R2 Path-filtered CI blind spots | Med | Include root config files (`pnpm-lock.yaml`, `pnpm-workspace.yaml`, workflow file itself) in filter lists |
| W-R-Playwright Browser binary download size | Low | Manual `workflow_dispatch` trigger only — never on PRs |

## Rollback Plan

- Pre-merge: `git reset --hard` the change branch.
- Post-merge / pre-deploy: revert the merge commit. 0b touches no migrations, no DB writes, no live services, so production state is unaffected.
- The change is purely additive (plus one config.yaml string edit), so a revert is mechanical.

## Dependencies

- Phase 0a (`repo-skeleton`) merged — provides the empty workspace and `.env.example` contract this phase fills in.
- `just`, `docker`, `uv`, `pnpm@10.33.3`, Node 22 LTS, Python 3.12 on contributor machines (documented in CONTRIBUTING).

## Success Criteria

- [ ] `just install` completes from a fresh clone (pnpm + uv)
- [ ] `just dev` boots web on `:3000` and api on `:8000` concurrently
- [ ] `curl localhost:8000/healthz` returns `{"status":"ok"}`
- [ ] `localhost:3000` renders "Fragwise"
- [ ] `just test` passes (1 vitest test + 1 pytest test)
- [ ] `just lint` is green (eslint + tsc + ruff + mypy strict)
- [ ] `docker compose up -d` brings up postgres (pg16) and redis healthy
- [ ] Three CI workflows execute on a PR with appropriate path-filter behavior
- [ ] `uv tree` in `apps/api` shows no `torch` or `transformers` entries
- [ ] `openspec/config.yaml` context line reads "Next.js 16 + Tailwind v4 + shadcn"
