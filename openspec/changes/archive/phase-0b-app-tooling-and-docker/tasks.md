# Tasks: Phase 0b — App Tooling and Docker

## Phase 1: Pre-flight

- [x] 1.1 Confirm working on a `phase-0b` branch off the latest main; verify 0a artifacts present (`apps/.gitkeep`, `packages/.gitkeep`, `openspec/config.yaml`, root `package.json`, `pnpm-workspace.yaml`); confirm none of the files in design.md "File Changes Summary" already exist (~3 min).

## Phase 2: Repo-root infrastructure

- [x] 2.1 Create `docker-compose.yml` per `design.md §"docker-compose.yml (repo root)"`. Verify volumes `fragwise-pgdata`, `fragwise-redisdata` and image pin `pgvector/pgvector:pg16` (~5 min).
- [x] 2.2 Create repo-root `justfile` per `design.md §"justfile (repo root)"`; assert all 14 recipes (`default`, `install`, `dev`, `dev-web`, `dev-api`, `test`, `test-web`, `test-api`, `lint`, `lint-web`, `lint-api`, `db-up`, `db-down`, `db-shell`) are listed by `just --list` (~5 min).
- [x] 2.3 Create repo-root `.prettierrc` per `design.md §".prettierrc"` (~2 min).
- [x] 2.4 Modify root `package.json` to add the `scripts` block per `design.md §"package.json (root) — add scripts"`; preserve existing `name`, `workspaces`, `packageManager` fields (~3 min).
- [x] 2.5 Append the 0b ignore section to root `.gitignore` per `design.md §".gitignore (root) — append section"` (~2 min).

## Phase 3: apps/api (Python / FastAPI / LangGraph)

- [x] 3.1 Delete `apps/api/.gitkeep`. Create `apps/api/pyproject.toml`, `apps/api/.python-version`, `apps/api/README.md` (one-line stub) per `design.md §"apps/api/pyproject.toml"` and §".python-version" (~5 min).
- [x] 3.2 Create `apps/api/src/fragwise_api/__init__.py`, `main.py`, `agent.py` per `design.md` (~7 min).
- [x] 3.3 Create `apps/api/tests/__init__.py`, `conftest.py`, `test_health.py`, `test_no_heavy_ml_deps.py` per `design.md` (~7 min).
- [x] 3.4 Run `cd apps/api && uv lock` to generate `uv.lock`; commit it (~3 min).
- [x] 3.5 Run `cd apps/api && uv sync && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy src` and confirm green (~5 min).
- [x] 3.6 Create `apps/api/Dockerfile` and `apps/api/.dockerignore` per `design.md`; build locally with `docker build apps/api` and run a container, then `curl localhost:8000/healthz` returns `{"status":"ok"}` (~10 min).

## Phase 4: apps/web bootstrap (hand-rolled, no create-next-app)

- [x] 4.1 Delete `apps/web/.gitkeep`. Create `apps/web/package.json`, `tsconfig.json`, `next.config.ts`, `postcss.config.mjs`, `eslint.config.mjs`, `components.json`, `.gitignore` per `design.md` (~10 min).
- [x] 4.2 Create `apps/web/app/globals.css`, `app/layout.tsx`, `app/page.tsx`, `components/theme-provider.tsx`, `lib/utils.ts` per `design.md` (~10 min).
- [x] 4.3 From repo root, run `pnpm install`; commit the generated `pnpm-lock.yaml` (~5 min).
- [x] 4.4 From `apps/web/`, run `npx shadcn@latest add button card input label dialog sonner dropdown-menu tabs separator badge`. Verify 10 files exist under `apps/web/components/ui/` and that `package.json` was updated with `@radix-ui/*` runtime deps; re-run `pnpm install` to refresh the lockfile (~10 min).
- [x] 4.5 Run `pnpm --filter web dev` once to let Next generate `apps/web/next-env.d.ts`; stop the server and commit the generated file (~3 min).

## Phase 5: apps/web testing (vitest + Playwright)

- [x] 5.1 Create `apps/web/vitest.config.ts`, `vitest.setup.ts`, `__tests__/page.test.tsx` per `design.md`; run `pnpm --filter web test` and confirm the smoke test passes (~5 min).
- [x] 5.2 Create `apps/web/playwright.config.ts` and `apps/web/e2e/home.spec.ts` per `design.md`; validate config with `pnpm --filter web exec playwright test --list` (~5 min).
- [x] 5.3 Run `pnpm --filter web lint && pnpm --filter web typecheck && pnpm --filter web build` and confirm all pass (~5 min).

## Phase 6: CI workflows

- [x] 6.1 Create `.github/workflows/web.yml` per `design.md`; lint with `actionlint` if installed, else verify YAML parses via `python -c "import yaml,sys;yaml.safe_load(open('.github/workflows/web.yml'))"` (~5 min).
- [x] 6.2 Create `.github/workflows/api.yml` per `design.md`; same YAML-parse assertion. Confirm `setup-uv` is SHA-pinned to `08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0` (~5 min).
- [x] 6.3 Create `.github/workflows/openspec.yml` per `design.md`; verify the bash proposal-presence script with `bash -n .github/workflows/openspec.yml` extraction (~5 min).
- [x] 6.4 Create `.github/workflows/e2e.yml` per `design.md`; assert it contains ONLY `workflow_dispatch:` (no `pull_request` / `push` triggers) (~3 min).

## Phase 7: Spec/config updates

- [x] 7.1 Update `openspec/config.yaml` `context:` block per `design.md §"openspec/config.yaml — context block"`. Confirm the line reads "Next.js 16 + Tailwind v4 + shadcn" and that the duplicated `Hosting:` line is removed (~3 min).

## Phase 8: Self-check / Success criteria

- [x] 8.1 From a clean clone state (or `git clean -xdf` of derived artifacts), run `just install` and confirm both pnpm + uv complete without errors (~5 min).
- [x] 8.2 Run `just dev` in one terminal and confirm web (`localhost:3000`) renders "Fragwise" and `curl localhost:8000/healthz` returns `{"status":"ok"}`; then stop with Ctrl-C (~5 min). [Recipe verified syntactically via `just --show dev`; live-execution skipped per orchestrator instructions.]
- [x] 8.3 Run `just test` and `just lint` from repo root; confirm both green (vitest + pytest, eslint + tsc + ruff + ruff-format + mypy strict) (~5 min).
- [x] 8.4 Run `just db-up`, confirm `docker compose ps` shows postgres + redis healthy, then `just db-shell` opens psql; exit, then `just db-down` (~5 min).
- [x] 8.5 Run `cd apps/api && uv tree` and grep-assert no `torch`, `transformers`, `sentence-transformers`, or `langchain` entries appear (~3 min).
