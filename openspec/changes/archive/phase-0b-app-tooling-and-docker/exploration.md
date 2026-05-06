# Exploration: phase-0b-app-tooling-and-docker

Investigation of the second slice of Fragwise foundation: per-app dev tooling (`apps/web` Next.js 15, `apps/api` FastAPI + LangGraph), local-dev infra (`docker-compose.yml`, `justfile`), and per-area GitHub Actions CI. Phase 0a already landed the repo skeleton (LICENSE, README, `.env.example`, `package.json`, `pnpm-workspace.yaml`, agent-context files, empty `apps/`, `packages/`, `data/` with `.gitkeep`). This exploration surfaces unknowns, risks, and trade-offs for 0b before `sdd-propose`.

## Current State

- Empty `apps/web/`, `apps/api/`, `packages/ontology/`, `data/seed/`, `data/scripts/` — only `.gitkeep` files.
- Root `package.json` is private, no deps, `packageManager` pinned to `pnpm@10.33.3`. `pnpm-workspace.yaml` declares `apps/*` and `packages/*`.
- No Docker, no `docker-compose.yml`, no `justfile`, no `.github/workflows/`, no test infra.
- `openspec/config.yaml` `testing.detected` is `false` for every layer; runners are `not_installed`. Updating that block is part of 0b's deliverables (or a follow-up `sdd-init` re-run).
- The original Phase 0 exploration (`openspec/changes/phase-0-foundation/exploration.md`) already locked these decisions: pnpm workspaces (U5), justfile (U6), uv for Python (U9), `pgvector/pgvector` image for compose+CI (U10), per-app workflows with path filters (U8). 0b is the change that makes them real.

## Affected Areas

This change creates new files only — no refactor.

- `apps/web/` — `package.json`, `tsconfig.json`, `next.config.ts`, `app/` directory (App Router), `app/layout.tsx`, `app/page.tsx`, `app/globals.css`, `postcss.config.mjs` (Tailwind v4), `components.json` (shadcn), `components/ui/` (shadcn primitives), `lib/utils.ts`, `eslint.config.mjs`, `.prettierrc`, `vitest.config.ts`, `vitest.setup.ts`, `playwright.config.ts`, `tests/e2e/.gitkeep` (or one trivial test), `next-env.d.ts`, `.gitignore` overrides.
- `apps/api/` — `pyproject.toml`, `uv.lock`, `app/__init__.py`, `app/main.py` (FastAPI factory + lifespan), `app/health.py`, `app/graph.py` (LangGraph stub), `tests/test_health.py`, `ruff.toml` (or `[tool.ruff]` in pyproject), `mypy` config (in pyproject), `.python-version`, `Dockerfile` (optional in 0b — see U-Infra-1).
- `packages/ontology/` — untouched (lives in 0c).
- Repo root — `docker-compose.yml`, `justfile`, possibly a `Makefile` shim (see U-Infra-2), updates to `.gitignore` for `.next/`, `.turbo/`, `playwright-report/`, `test-results/`.
- `.github/workflows/` — `web.yml`, `api.yml`, `openspec.yml` (3 separate workflows with path filters).
- `openspec/config.yaml` — update `testing` block to reflect installed runners (vitest, pytest, ruff, mypy, eslint, tsc).
- `CLAUDE.md` / `AGENTS.md` — minor edits to swap "Configured in phase-0b" notes for actual config paths once they exist (probably handled in 0b sdd-apply).

## Sub-area 1 — `apps/web` (Next.js 15 + Tailwind + shadcn + tests)

### Web Unknowns

#### U-Web-1. Next.js scaffolding strategy: `create-next-app --example` vs hand-rolled vs shadcn `init -t next --monorepo`
Three viable paths verified via Context7:

1. **`pnpm create next-app apps/web --typescript --eslint --tailwind --app --src-dir`** — official, uses defaults that `create-next-app` enables (TS, ESLint, Tailwind v4 via `@tailwindcss/postcss`, App Router, Turbopack, import alias). This is the "supported happy path." Generates a `tailwind.config` only if user says no to Tailwind v4; default in current 16.x line is v4 + `@tailwindcss/postcss` + `@import "tailwindcss"` in `globals.css` — no JS config file at all.
2. **`npx shadcn@latest init -t next --monorepo`** — verified via Context7 (`/shadcn-ui/ui` docs, dated 2026-03 cli-v4 changelog): scaffolds **`apps/web` + `packages/ui` with Turborepo**. This conflicts with our 0a decision (bare pnpm workspaces, no Turborepo) and adds an unwanted `packages/ui`. Not recommended unless we want to revise the monorepo shape.
3. **Hand-rolled** — write `package.json`, `tsconfig.json`, `next.config.ts`, `app/`, `postcss.config.mjs`, `globals.css` from spec/design templates, then run `pnpm install` and `pnpm shadcn@latest add button` etc. Tightest control, lowest surprise, but the most lines in `design.md`.

**Open question for the user**: do we use `create-next-app` (option 1, accept its choices) or hand-roll (option 3)? Option 2 is rejected because it forces Turborepo + `packages/ui`. **Tentative recommendation: option 3 (hand-rolled).** SDD wants every byte to be intentional, and `create-next-app` writes a README, `public/` icons, fonts wiring, and other artifacts we'd need to clean up. Hand-rolling 6 files is cheaper than auditing what `create-next-app` produced.

#### U-Web-2. Next.js version pin
The locked stack says "Next.js 15." Context7 confirms current line is **Next.js 16.x** (versions seen: 15.4.0-canary.82, 16.0.3, 16.1.0, 16.1.1, 16.1.5, 16.1.6, 16.2.2 across the index). 15.1.x and 15.1.11 still exist. We have to choose:
- Stay on 15.x latest (15.1.x range) — matches the locked-stack wording, but is technically prior-major and getting only patch maintenance.
- Move to 16.x — current major; Context7 docs path `/vercel/next.js/v16.2.2` is the active reference. App Router, Turbopack default, RSC default — all the same.
- The user's `openspec/config.yaml` `context:` says "Next.js 15" verbatim. Either we update the config or pin to 15.

**Open question for the user**: pin Next.js to `^15.1` (literal-stack-match) or `^16.2` (current)? **Tentative recommendation: 16.x.** Phase 0b is the right time to bump because no app code has been written yet; sticking with 15 just to honor the config string is a wash. If the user agrees, update `config.yaml` `context:` accordingly.

#### U-Web-3. Tailwind v3 vs v4
Context7 (`/tailwindlabs/tailwindcss.com`) makes clear that Tailwind **v4 is the current line** and the install pattern is fundamentally different from v3:
- v3: `tailwind.config.ts` + `tailwind.config.content` array + `@tailwind base/components/utilities` directives.
- v4: `@tailwindcss/postcss` PostCSS plugin, single `@import "tailwindcss"` in CSS, **no JS config file by default** — config is CSS-first via `@theme { ... }` blocks.
- The Phase 0a design.md still says "Tailwind v3" in places (`tailwind.config.ts`). That's stale.

**Open question for the user**: confirm Tailwind v4 (current default with `create-next-app`). v3 is supported but deprecated. **Tentative recommendation: v4.** Removes the `tailwind.config.ts` file entirely and sets up theming via `@theme` in `globals.css`. shadcn supports v4.

#### U-Web-4. shadcn CLI invocation
Context7 (`/shadcn-ui/ui`) confirms the CLI is **`shadcn`** (not `shadcn-ui`). Current command shape:
```
npx shadcn@latest init        # interactive, in existing project
npx shadcn@latest add button card dialog ...
```
The package was renamed from `shadcn-ui` to `shadcn` (cli v4 changelog March 2026). Old `npx shadcn-ui@latest` instructions on the web are outdated. We pin the version: `shadcn@2.9.0` or `shadcn_3_2_1` are the current Context7-listed releases.

**Open question for the user**: which initial shadcn primitives ship in 0b? The brief says "primitives" but doesn't enumerate. Reasonable starter set: `button`, `card`, `input`, `label`, `dialog`, `dropdown-menu`, `sheet`, `tooltip`, `separator`, `badge`. About 10 primitives, ~3K LOC of generated `components/ui/`. **Tentative recommendation: install the 10 primitives above.** It's cheap, catches monorepo path bugs, and means later phases don't have to think about shadcn. If we want a smaller set, defaults can be just `button` and `card` to prove the pipeline.

#### U-Web-5. TypeScript strictness, path aliases, RSC default
- `tsconfig.json` `strict: true` — should be obvious yes. Question is whether to also enable `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` — these catch real bugs but increase friction. Pragmatic default: `strict: true`, leave the extras off and revisit if pain emerges.
- Path alias: `@/*` -> `./src/*` if we use `--src-dir`, or `./*` from app root. Convention from the Next docs and shadcn defaults is `@/*` -> `./src/*`. **Tentative recommendation: use `src/` layout** to keep `app/`, `components/`, `lib/` under `src/` and away from config files at the package root. shadcn `components.json` will be generated to match.
- RSC default: server component default (App Router default). `"use client"` only where needed. No decision required; just document.

#### U-Web-6. ESLint config: flat config or legacy
Next.js 15+ uses the new flat config (`eslint.config.mjs`) from `eslint-config-next`. Context7 shows this snippet:
```js
import nextVitals from 'eslint-config-next/core-web-vitals'
import nextTs from 'eslint-config-next/typescript'
```
**Tentative recommendation: flat config.** No legacy `.eslintrc`. Add Prettier integration via `eslint-config-prettier` (disables ESLint rules that conflict with Prettier).

#### U-Web-7. Prettier config and lint-staged
- `.prettierrc.json` with sensible defaults (`semi: false`, `singleQuote: true`, `printWidth: 100` — or just defaults). Bikeshed.
- `lint-staged` + `husky`: yes/no. See U-Infra-3.

#### U-Web-8. Vitest setup details
- Use `vitest` v3+ (current stable per Context7 is `v3_2_4`; v4 exists but is fresh). Pair with `@testing-library/react`, `@testing-library/jest-dom`, `@vitest/ui` (optional).
- Environment: `jsdom` (via `vitest.config.ts` `test.environment`).
- Path alias resolution in vitest: `vite-tsconfig-paths` plugin or manual alias in `vitest.config.ts`. **Tentative recommendation: `vite-tsconfig-paths`** (zero-config, reads `tsconfig.json`).
- Sample test: assert the home page renders the string "Fragwise". Just one passing test to prove the runner.

#### U-Web-9. Playwright: full setup or stub?
Brief says "E2E placeholder, not full tests yet." Two interpretations:
- Install `@playwright/test`, ship `playwright.config.ts`, `tests/e2e/example.spec.ts` (one passing test that hits the dev server), wire into CI as a separate job that boots the app.
- Install nothing — just leave a `tests/e2e/.gitkeep` and a TODO in the README. Defer Playwright entirely to a later phase.

The trade-off: option 1 adds ~150MB browser binaries to local dev (`pnpm dlx playwright install`) and meaningful CI minutes; option 2 leaves a half-finished promise. **Tentative recommendation: install + config + one trivial test, but do NOT run it in default CI.** Add a manual workflow_dispatch entry-point in `web.yml` so it's there when needed but doesn't slow PRs.

#### U-Web-10. next-intl / i18n
Brief asks: "do we use `next-intl` from day 1 or defer?" Day 1 in 0b is overkill — ontology is English-first, and i18n has surface area beyond just a library. **Tentative recommendation: defer.** Don't install `next-intl`; add a TODO in the README and the proposal explicitly defers to a later phase.

#### U-Web-11. Bare home page content
Brief: "A bare home page rendering 'Fragwise' with the locked design philosophy (placeholder)." Concretely, the `app/page.tsx` should just render the project name. We may want one shadcn component visible (a `Button` saying "Coming soon") to prove shadcn integration works visually. **Tentative recommendation: render `<h1>Fragwise</h1>` plus one shadcn `<Button>` so the page is a living smoke-test of the toolchain.**

#### U-Web-12. Storybook
Brief: "Storybook for shadcn primitives: yes (better dev) or no (heavier setup, defer)?" Storybook adds another build target, another dev server, another dependency tree. Trade-off: nice for primitive review now, but the real design comes from `frontend-design` skill in a later phase. **Tentative recommendation: defer Storybook.** Revisit when there are >20 components or designers on the team.

### Web Risks

- **W-R1 — Tailwind v4 + monorepo path resolution**: Tailwind v4's content detection is automatic via `@tailwindcss/postcss` walking the `app/` and `components/` directories. Monorepo paths can confuse the auto-detector if shadcn primitives live in a separate `packages/ui`. Since we're keeping primitives inside `apps/web/components/ui/` (no `packages/ui`), the risk is low. **Mitigation**: keep all class-emitting code inside `apps/web/`.
- **W-R2 — Next.js 15 vs 16 mismatch with config.yaml**: see U-Web-2.
- **W-R3 — Vitest path-alias resolution**: forgetting `vite-tsconfig-paths` makes every `@/*` import in tests fail with cryptic resolver errors. Standard footgun for Next-on-Vitest.
- **W-R4 — Playwright in CI eats minutes**: full-browser cold installs are ~5min/run and image cache is finicky on GitHub Actions. **Mitigation**: gate Playwright behind `workflow_dispatch` or a label.
- **W-R5 — shadcn copy-paste model in monorepo**: shadcn writes files into your repo (it doesn't ship as a library). On `pnpm install --frozen-lockfile` in CI we don't re-run `shadcn add`, so the committed `components/ui/` IS the source of truth. Means PRs touching shadcn primitives modify real files — fine, but worth documenting in CONTRIBUTING.

### Web Trade-offs

| Decision | Option A | Option B | Recommendation |
|---|---|---|---|
| Scaffold | `create-next-app` (auto) | Hand-rolled | Hand-rolled |
| Next major | 15.x | 16.x | 16.x; update config |
| Tailwind | v3 | v4 | v4 |
| Layout | flat (no `src/`) | `src/` | `src/` |
| Initial shadcn primitives | minimal (1-2) | starter set (~10) | ~10 |
| Playwright | full + run in CI | install + manual trigger | manual trigger |
| Storybook | now | defer | defer |
| `next-intl` | now | defer | defer |
| Pre-commit hooks | husky+lint-staged | none | see U-Infra-3 |

## Sub-area 2 — `apps/api` (FastAPI + LangGraph + uv + ruff + mypy + pytest)

### API Unknowns

#### U-API-1. Python version: 3.12 vs 3.13
Brief says 3.12. Python 3.13 is GA (Oct 2024) and has free-threaded interpreter as opt-in plus better error messages. Most ML/AI Python libs are now testing on 3.13.
- **3.12** — broadest wheel coverage, all our deps (fastapi, langgraph, sentence-transformers if ever added, asyncpg, sqlalchemy) ship 3.12 wheels everywhere.
- **3.13** — newer features, but some C-extension wheels may still be 3.12-only on day-one of a new release.

**Tentative recommendation: 3.12**, pinned via `requires-python = ">=3.12,<3.13"` and `.python-version: 3.12`. We can bump after verifying every dep has 3.13 wheels.

#### U-API-2. uv: workspace mode or single-project mode
Context7 (`/astral-sh/uv` workspace docs) confirms uv supports a workspace pattern with `[tool.uv.workspace] members = [...]` and a single `uv.lock` at the workspace root.
- **Single-project mode**: `apps/api/pyproject.toml` is a normal project, `uv.lock` lives next to it. `cd apps/api && uv sync`. Simple, works today.
- **Workspace mode**: `pyproject.toml` at repo root declares workspace members; `apps/api` is one member, future Python packages (e.g., `data/scripts/` if it becomes a package) can join. One shared `uv.lock`.

The key trade-off: workspace mode shines when there are >1 Python member. Today there's only `apps/api`. Adding `data/scripts/` as a member in a later phase is mechanical. **Tentative recommendation: single-project mode in `apps/api/`.** Avoid root-level `pyproject.toml` (it confuses humans into thinking there's a top-level Python project). Lift to a workspace later if/when `data/scripts/` becomes a package.

#### U-API-3. Lockfile committed?
Yes, `uv.lock` MUST be committed. Confirmed in `/astral-sh/uv` docs: "This file should be checked into version control." No question.

#### U-API-4. FastAPI version
Current Context7 versions: `0.115.13`, `0.116.1`, `0.118.2`, `0.122.0`, `0.128.0`. **Tentative recommendation: pin to `^0.128`** (current stable). Lifespan API is the same across this whole range, so churn is low.

#### U-API-5. App factory pattern vs single `main.py`
Two patterns:
- **Single `main.py`** — `app = FastAPI(...)`, routes attached directly. Simple, 5 lines.
- **App factory** — `def create_app() -> FastAPI:` returning a configured instance, called from `main.py` (and from tests). Lets tests pass settings overrides, mock dependencies, etc.

Since 0b only ships `/healthz` and a no-op LangGraph import, the factory is overkill *today*. But adopting it now is cheap and saves a refactor in 0c when the DB pool, Redis client, and dependency injection arrive. **Tentative recommendation: app factory.** ~15 LOC, sets up the pattern.

#### U-API-6. Lifespan handler shape
Context7 (`/fastapi/fastapi/0.128.0`) confirms the modern pattern is:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown
app = FastAPI(lifespan=lifespan)
```
For 0b, lifespan body is empty (no DB pool yet) but the structure should be present so 0c can plug in `asyncpg`/`sqlalchemy` engines without a refactor. **Tentative recommendation: ship a no-op lifespan.**

#### U-API-7. LangGraph: package and version
Context7 (`/langchain-ai/langgraph`) confirms:
- Package name is `langgraph` (NOT `langchain-langgraph`). Install: `pip install -U langgraph`.
- Current versions: `0.6.7`, `1.0.3`, `1.0.4` (prebuilt), `1.0.6`, `1.0.8`. **The 1.0 line is GA.**
- Minimal stub:
  ```python
  from langgraph.graph import START, StateGraph
  from typing_extensions import TypedDict

  class State(TypedDict):
      text: str

  def echo(state: State) -> dict:
      return {"text": state["text"]}

  graph = StateGraph(State)
  graph.add_node("echo", echo)
  graph.add_edge(START, "echo")
  compiled = graph.compile()
  ```
- This proves the import works without pulling LangChain. We do NOT install `langchain` or `langchain-openai` in 0b.

**Tentative recommendation: pin `langgraph ^1.0.8`**, ship the no-op StateGraph, no LangChain.

#### U-API-8. Memory/checkpointer
Brief asks about LangGraph's checkpointer (Memory, Postgres-backed, Redis-backed). All deferred to 0c (or later). **Tentative recommendation: don't install any checkpointer in 0b.** The compile call without a checkpointer just runs in-process.

#### U-API-9. ruff config
- Latest ruff is fast-moving; pin to `>=0.6,<1.0` or just `>=0.6`. Configure in `[tool.ruff]` section of `pyproject.toml`, not a separate `ruff.toml`. Enable `E,F,I,UP,B,SIM,W,N,RUF` rule families to start. Line length 100 (matches Prettier).
- Format with ruff (`ruff format`), drop black entirely. Ruff's formatter is black-compatible.

#### U-API-10. mypy config
Strict mode (`--strict`) is the goal per `CLAUDE.md` "Python types: mypy, Strict mode in `apps/api`." Configure in `[tool.mypy]` in `pyproject.toml`. Pin mypy `>=1.8`. **Tentative recommendation: strict, with one allowlist for `langgraph` if its type stubs are incomplete.** Test will reveal which.

#### U-API-11. pytest + httpx
- pytest `>=8`, pytest-asyncio `>=0.24` for async tests, httpx `>=0.27` for the FastAPI test client (`httpx.AsyncClient(app=app)` is the modern pattern; the deprecated `TestClient` from starlette also works but blocks).
- Sample test: spin the FastAPI app, call `/healthz`, assert `200 OK` and `{"status": "ok"}`.
- **Tentative recommendation: use `httpx.AsyncClient`** with `pytest-asyncio` `asyncio_mode = auto`.

#### U-API-12. Health endpoint shape
- `/healthz` (Kubernetes convention) or `/health` (simpler)? Brief says `/healthz`. Done.
- Response: `{"status": "ok"}` or richer (DB ping, Redis ping)? In 0b there's nothing to ping. Future phases will add a `/readyz` for deep checks, leaving `/healthz` as a liveness probe. **Tentative recommendation: 0b ships only `/healthz` returning `{"status": "ok"}`. Add `/readyz` in 0c when DB exists.**

#### U-API-13. Dockerfile in 0b?
Brief lists "Dockerfile" only implicitly (the original Phase 0 exploration did, the 0b brief doesn't explicitly). Two options:
- **Ship a multi-stage `apps/api/Dockerfile`** based on `astral-sh/uv-docker-example` (Context7 has 34 snippets dated current). Useful for local-dev parity and for CI to build-test the image.
- **Defer to a later phase** that handles Fly.io deploy (probably called `phase-1-deploy` or similar).

**Tentative recommendation: ship a minimal `apps/api/Dockerfile` in 0b.** It's <50 lines and unblocks "I want to test self-hosting with `docker compose up`" use cases. The image won't be deployed yet but local-compose can use it.

### API Risks

- **A-R1 — uv velocity**: uv is fast-moving (Context7 shows monthly+ releases). Pin via `setup-uv` action input and via `pyproject.toml` `[tool.uv] required-version = ">=0.5"`. Document.
- **A-R2 — LangGraph 1.0 churn**: 1.0 is GA but recent. Read the migration guide before pinning to a 1.x release. Pin tightly (`==1.0.8` or `~=1.0.8`) initially.
- **A-R3 — Heavy ML deps creeping in**: brief explicitly defers sentence-transformers / torch. Verify `uv add langgraph` does NOT pull in torch/transformers transitively. Run `uv tree` after install in `sdd-verify` to assert resident set. **Mitigation**: a pytest test that imports `langgraph` and checks `import torch` raises ImportError (or skip if installed).
- **A-R4 — mypy strict + LangGraph stubs**: if langgraph's type stubs are missing or incomplete, strict mypy will fail. **Mitigation**: targeted `[[tool.mypy.overrides]]` block for `module = "langgraph.*", ignore_missing_imports = true` if needed.
- **A-R5 — Python 3.12 wheels in CI containers**: ubuntu-latest in GitHub Actions provides Python 3.12 by default; uv handles 3.12 install if not present. Risk is negligible but pin uv's Python via `setup-uv` `python-version: "3.12"`.

### API Trade-offs

| Decision | Option A | Option B | Recommendation |
|---|---|---|---|
| Python version | 3.12 | 3.13 | 3.12 |
| uv layout | workspace | single-project | single-project |
| App pattern | factory | inline | factory |
| LangGraph version | 0.6.x | 1.0.8 | 1.0.8 |
| Checkpointer | install Postgres/SQLite | none | none |
| Test client | starlette TestClient | httpx.AsyncClient | httpx.AsyncClient |
| Dockerfile | now | defer | now |

## Sub-area 3 — Repo-root Infrastructure (`docker-compose.yml`, `justfile`, CI)

### Infra Unknowns

#### U-Infra-1. docker-compose.yml: services and image pins
- **Postgres**: Original Phase 0 exploration recommended `pgvector/pgvector:pg16`. Context7 (`/pgvector/pgvector`) reveals the current actively-published tag is `pgvector/pgvector:pg18-trixie` — i.e. they've moved to PG18 and even use Debian Trixie base. Older tags (`pg16`, `pg17`) are still available but aren't the bleeding edge.
- **Redis**: `redis:7-alpine` is the standard. `redis:7.4-alpine` is the latest 7.x.
- **Volumes**: named volumes for both (`pgdata`, `redisdata`) so a `docker compose down` doesn't wipe state; only `docker compose down -v` does.
- **Ports**: `5432:5432` for Postgres, `6379:6379` for Redis on local dev. In CI we leave them unmapped.
- **Profiles**: brief asks "profiles (dev only?)". Compose profiles let you have services that only start when you opt in (e.g., `--profile dev` for tools, `--profile ci` for headless variants). For 0b we have only two services and both are needed locally and in CI. **Tentative recommendation: no profiles in 0b**; add when we have an optional service (e.g., a mailhog or a minio-for-R2 mock).
- **`.env` for compose**: Compose reads `.env` from the directory it's invoked in. Since `.env` is gitignored, compose-only config (e.g. `POSTGRES_PASSWORD` for local dev) lives in `.env.example` and gets copied to `.env` by the developer. Document this in the README setup section.

**Open question for the user**: pin to `pgvector/pgvector:pg16` (matches original 0a/0b plan), `pg17`, or `pg18-trixie` (current)? Neon Postgres production is PG16/17. **Tentative recommendation: `pgvector/pgvector:pg16`** to match Neon's default. Bump in lockstep with Neon, not ahead.

#### U-Infra-2. Makefile shim?
Brief asks: "justfile vs Makefile fallback for contributors who don't have `just`?" Trade-offs:
- A second top-level file (Makefile) duplicating recipes is a maintenance burden and risks drift.
- `just` is one-line install on every platform (`brew install just`, `cargo install just`, `apt install just`).
- The original Phase 0 exploration (U6) chose justfile and explicitly said "Add a Makefile shim only if you get explicit user pushback."

**Tentative recommendation: justfile only, no Makefile shim.** Add a one-line in CONTRIBUTING saying "install just." Re-evaluate if a contributor objects.

#### U-Infra-3. Pre-commit hooks: framework, scope
Three viable approaches:
- **`pre-commit` (Python framework, runs all hooks)** — language-agnostic, has built-in hooks for ruff, prettier, eslint via plugins. Stable, well-known.
- **`lefthook`** — Go binary, fast, configured via `lefthook.yml`. Good monorepo support.
- **`husky` + `lint-staged`** — JS-side; husky installs git hooks, lint-staged runs eslint/prettier on staged files. Doesn't natively cover Python.
- **None** — let CI catch lint/format issues; no local enforcement.

The catch-early value is real (especially for big lint-only churn diffs), but local hooks add friction and confuse first-time contributors who don't have `pre-commit` installed.

**Open question for the user.** Pick one of:
- (a) `pre-commit` framework — covers ruff, prettier, eslint, all in one config. **Tentative recommendation if hooks are wanted.**
- (b) Skip pre-commit hooks entirely; rely on CI. Simpler for OSS contributors.

**Tentative recommendation: skip in 0b**, document the option in CONTRIBUTING. Adding hooks later is mechanical and doesn't break history.

#### U-Infra-4. justfile recipe shape
Brief lists the recipes: `install`, `dev` (concurrently runs web + api), `dev-web`, `dev-api`, `test`, `test-web`, `test-api`, `lint`, `lint-web`, `lint-api`, `db-up`, `db-down`, `db-shell`. Notes:
- `dev` running both apps concurrently: justfile doesn't have a built-in concurrent runner, so we use `&` shell trick or a tool like `concurrently` (Node) / `overmind` / `mprocs`. **Tentative recommendation: `mprocs` or background `&` with `wait`.** Or use `tmux` panes, but that's tool-heavy. Simplest: `dev: just dev-web & just dev-api & wait`.
- `db-shell`: `docker compose exec postgres psql -U fragwise fragwise`. Trivial.
- `install` should: `pnpm install` AND `cd apps/api && uv sync`. One recipe both languages.

#### U-Infra-5. CI cache strategy
Verified via Context7 (`/astral-sh/setup-uv`):
- **uv** caching: `astral-sh/setup-uv@v8` with `enable-cache: true` and `cache-dependency-glob: "**/uv.lock"`. Caches the uv install + downloaded packages. Pin via SHA (Context7 example: `08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0`).
- **pnpm** caching: `pnpm/action-setup@v4` then `actions/setup-node@v4` with `cache: 'pnpm'`. Standard.
- **Playwright browsers**: separate cache key on `~/.cache/ms-playwright`.

**Tentative recommendation**: enable cache for both, pin actions to commit SHAs (security best practice for OSS), use `cache-dependency-glob` keyed on lock files.

#### U-Infra-6. CI matrix
- Brief: "Matrix testing across Python versions or pin to one?" We use uv-managed Python and pin to 3.12. No matrix needed in 0b.
- Web side: pin Node to one version (the version pnpm@10 supports, which is Node `>=18.12`). **Tentative recommendation: Node 22 LTS, single version, no matrix.**

#### U-Infra-7. CI path filters and missed cross-cutting changes
Brief raises this risk explicitly. Path filters in `web.yml`/`api.yml` (`paths: ['apps/web/**', 'package.json', 'pnpm-lock.yaml']`) mean a change to `package.json` triggers `web.yml` even if no `apps/web/**` file changed. Document the filter list in the workflow comments. **Tentative recommendation: include `pnpm-workspace.yaml`, `package.json`, `pnpm-lock.yaml`, and the workflow file itself in `web.yml`'s path filters; symmetrically for api.yml.**

#### U-Infra-8. openspec.yml workflow
Brief: "runs on any PR; basic check that any new change in `openspec/changes/` has at minimum a `proposal.md`." Concretely:
- Detect changed files under `openspec/changes/{name}/` that are NOT in `archive/`.
- For each new directory, assert `proposal.md` exists.
- Implementable in a 30-line bash step or a small Python script.

**Tentative recommendation: bash-only step.** No new dependency.

#### U-Infra-9. Sentry / OpenTelemetry placeholder
Brief asks: include a stub now or defer? Adding observability infra without a use case is overkill. **Tentative recommendation: defer.** Sentry/OTel land alongside the first deploy phase.

### Infra Risks

- **I-R1 — pgvector tag drift**: pinning `pg16` keeps us aligned with Neon, but pgvector now publishes `pg18-trixie` as latest. Risk: docs become stale. **Mitigation**: doc comment in `docker-compose.yml` next to the image tag.
- **I-R2 — Path-filtered CI misses cross-cutting refactors**: e.g., updating ESLint config in root affects `apps/web` but if it's at the repo root the filter might miss it. **Mitigation**: add config files to filter lists explicitly; periodic full-CI run on `main` after merge as backstop.
- **I-R3 — GitHub Actions free-tier minute budget**: brief notes this. With caching (uv + pnpm + Playwright) and per-app filters, expected usage is well under the public-repo unlimited tier. Containers/`docker compose up` in CI eats minutes; we likely don't need compose-in-CI in 0b (the api tests don't require Postgres yet), so leave compose-in-CI for 0c.
- **I-R4 — `just dev` cross-platform behavior**: `just dev-web & just dev-api & wait` works on macOS/Linux but breaks on Windows. **Mitigation**: document Windows users use `just dev-web` and `just dev-api` in separate terminals; the unified `dev` recipe is best-effort for POSIX.
- **I-R5 — Compose `.env` clash with Next.js `.env.local`**: Next.js reads `.env.local`, compose reads `.env`. They coexist but a contributor might dump everything in `.env` and wonder why Next doesn't see it. **Mitigation**: document each tool's env discovery path in CONTRIBUTING.

### Infra Trade-offs

| Decision | Option A | Option B | Recommendation |
|---|---|---|---|
| Postgres image tag | `pg16` (Neon-aligned) | `pg18-trixie` (current) | `pg16` |
| Pre-commit hooks | yes (pre-commit framework) | no (CI only) | no |
| Makefile shim | yes | no | no |
| `just dev` runner | `&`+wait | `mprocs` | `&`+wait |
| CI cache | actions/setup-* cache | manual `actions/cache` | setup-* cache |
| Compose in CI | run pg+redis service containers | none in 0b | none in 0b |
| Sentry/OTel | stub now | defer | defer |
| Dockerfile in 0b | yes (api) | defer | yes (api) |
| openspec.yml | bash check | python script | bash |

## Cross-cutting Open Questions for the User

Before `sdd-propose`, we need explicit decisions on:

1. **Q1 — Next.js major**: pin `^15` (literal stack match) or `^16` (current)? Tentative: 16; update `config.yaml` accordingly.
2. **Q2 — Postgres image tag**: `pg16` (Neon-aligned) or `pg18-trixie` (current)? Tentative: `pg16`.
3. **Q3 — Pre-commit hooks**: yes (pre-commit framework) or no (CI only)? Tentative: no.
4. **Q4 — Initial shadcn primitive set**: full starter (~10) or minimal (button/card)? Tentative: ~10.
5. **Q5 — Playwright**: install + manual-trigger CI, or skip entirely until later? Tentative: install, manual trigger.
6. **Q6 — Storybook**: now or defer? Tentative: defer.
7. **Q7 — Dockerfile in 0b**: ship `apps/api/Dockerfile` now or defer? Tentative: ship.
8. **Q8 — uv mode**: single-project or workspace? Tentative: single-project.
9. **Q9 — Tailwind major**: v3 or v4? Tentative: v4.
10. **Q10 — `next-intl`**: now or defer? Tentative: defer.

## Recommendation: Should 0b Be Split Further?

**No — keep 0b as a single change**, but with caveats.

The three sub-areas (web / api / infra) are tightly coupled by `justfile` and `docker-compose.yml`: the justfile recipes reference both apps; docker-compose's `db-up` is needed for `apps/api` integration tests when those land; CI workflows need to know about both. Splitting into 0b-web / 0b-api / 0b-infra creates a 3-way merge dance with chicken-and-egg ordering (e.g., 0b-infra's CI workflow can't be tested until 0b-web and 0b-api both exist). The total task count is ~25 items but they group cleanly into the three buckets — manageable in a single `tasks.md` if grouped by phase (infrastructure setup, web setup, api setup, CI setup, verification).

Caveat: if `tasks.md` exceeds 30 items after `sdd-tasks` runs, revisit. A specific natural cut would be **0b** (web + api + docker-compose + justfile + minimal CI) and **0b-2** (Playwright + observability stubs + Storybook + advanced CI) — i.e., split by *optional* features. But the brief's "minimum viable tooling" framing suggests we resist scope creep into 0b-2 territory now and just defer Playwright-in-CI / Storybook / pre-commit / Sentry to later phases. That keeps 0b unified.

## Ready for Proposal

**Partial.** The orchestrator should report back to the user with the 10 cross-cutting questions above. Most have tentative recommendations and the user can ratify in bulk. Once those decisions land (especially Q1, Q2, Q3, Q9), `sdd-propose` can run against `phase-0b-app-tooling-and-docker` with high confidence.

---

## Return Envelope

**Status**: success
**Summary**: Exploration of phase-0b-app-tooling-and-docker complete. Surfaced 10 cross-cutting open questions for the user (Next.js major, Tailwind major, Postgres tag, pre-commit, shadcn primitive set, Playwright, Storybook, Dockerfile, uv mode, next-intl). Verified library state via Context7 for Next.js 16.x, Tailwind v4, shadcn (renamed CLI), uv workspace docs, FastAPI 0.128 lifespan, LangGraph 1.0.8 minimal-graph stub, and pgvector image tags (current `pg18-trixie`, but tentative recommendation is `pg16` to match Neon). Recommend keeping 0b as a single change (do not split further) but defer Storybook, Playwright-in-CI, pre-commit hooks, and Sentry/OTel.
**Artifacts**: `openspec/changes/phase-0b-app-tooling-and-docker/exploration.md`
**Next**: User decisions on Q1-Q10, then `sdd-propose` for `phase-0b-app-tooling-and-docker`.
**Risks**: 10 risks itemized (W-R1..5 web, A-R1..5 api, I-R1..5 infra). The most material ones: Tailwind v4 monorepo content detection (W-R1), LangGraph 1.0 churn / heavy-ML transitive deps (A-R2/A-R3), pgvector tag drift vs Neon (I-R1), CI path-filter cross-cutting misses (I-R2).
**Skill Resolution**: fallback-path — loaded `~/.claude/skills/sdd-explore/SKILL.md` plus `_shared/sdd-phase-common.md` and `_shared/openspec-convention.md`. Project standards block was not pre-injected.
