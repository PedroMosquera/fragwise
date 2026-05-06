# Design: Phase 0b — App Tooling and Docker

## Technical Approach

Make the empty 0a workspace executable. `apps/web` is a hand-rolled Next.js 16
+ React 19 + Tailwind v4 + shadcn project (no `create-next-app`, no shadcn
`--monorepo`). `apps/api` is a uv-managed single-project FastAPI app with an
app-factory + no-op lifespan and a compiled LangGraph 1.x stub. Repo-root
adds `docker-compose.yml` (postgres+redis), `justfile` (14 recipes), four
GitHub Actions workflows (web, api, openspec, e2e), and a config-context
update. No domain logic — toolchain only.

All version pins below were verified via Context7 on 2026-05-06 against the
following library IDs: `/vercel/next.js/v16.2.2`,
`/tailwindlabs/tailwindcss.com`, `/shadcn-ui/ui`, `/fastapi/fastapi/0.128.0`,
`/langchain-ai/langgraph/1.0.8`, `/astral-sh/uv-docker-example`,
`/astral-sh/setup-uv` (v8.1.0).

## Verified Version Pins (2026-05-06)

| Package / image | Pin | Source |
|---|---|---|
| Next.js | `^16.2.2` | Context7 `/vercel/next.js/v16.2.2` |
| React / react-dom | `^19.0.0` | Next 16 minimum (Context7 v15 upgrade note) |
| Tailwind CSS | `^4.0.0` | Context7 `/tailwindlabs/tailwindcss.com` |
| `@tailwindcss/postcss` | `^4.0.0` | Same source |
| shadcn CLI | `shadcn@latest` (current `3.5.0`) | Context7 `/shadcn-ui/ui` |
| Vitest | `^3.2.4` | Current stable |
| `@playwright/test` | `^1.49.0` | Current stable |
| `eslint-config-next` | `^16.2.2` | matches Next |
| Prettier | `^3.4.0` | Current stable |
| FastAPI | `>=0.128.0,<1.0` | Context7 `/fastapi/fastapi/0.128.0` |
| `uvicorn[standard]` | `>=0.32,<1.0` | Current stable |
| LangGraph | `~=1.0.8` | Context7 1.0.8 GA tag |
| httpx | `>=0.27,<1.0` | TestClient/AsyncClient compatible |
| ruff | `>=0.7,<1.0` | Current stable, formatter+linter |
| mypy | `>=1.13,<2.0` | Current stable |
| pytest | `>=8.3,<9.0` | Current stable |
| pytest-asyncio | `>=0.24,<1.0` | Current stable |
| Python (Dockerfile) | `python:3.12-slim-bookworm` | Verified via uv-docker-example |
| uv (Dockerfile builder) | `ghcr.io/astral-sh/uv:0.5-bookworm-slim` | Verified via uv-docker-example |
| `pgvector/pgvector` | `pg16` | Pinned for Neon parity |
| Redis | `redis:7-alpine` | Standard |
| Node (CI) | `22` (LTS) | Current LTS |
| pnpm | `10.33.3` | Carried from 0a (root `package.json`) — confirmed current |
| `actions/checkout` | `@v4` | Current |
| `actions/setup-node` | `@v4` | Current |
| `actions/setup-python` | `@v5` | Current |
| `pnpm/action-setup` | `@v4` | Current |
| `astral-sh/setup-uv` | `@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0` | Pinned to SHA per Context7 best practice |

## Architecture Decisions (ADRs)

### ADR-0005: Next.js 16 + Tailwind v4

**Status**: Accepted.
**Context**: 0a's config text said "Next.js 15 + Tailwind". 0b is the right
moment to bump because no application code is committed yet. Tailwind v4 is
the current stable line and is fundamentally different from v3 (CSS-first
config, no `tailwind.config.ts`, single `@import "tailwindcss";` directive).
Next.js 16 is the active major (Context7 surfaces `v16.2.2` as the latest
stable). The community ecosystem (shadcn, eslint-config-next, vitest plugins)
is already on Tailwind v4 + Next 16.
**Decision**: Pin Next.js `^16.2.2`, React/react-dom `^19.0.0`, Tailwind
`^4.0.0`, `@tailwindcss/postcss` `^4.0.0`. Update `openspec/config.yaml`
context line accordingly. No `tailwind.config.ts` file.
**Consequences**: Bleeding-edge enough that future patches will roll quickly;
mitigated by caret ranges on patch level. Tailwind v4 monorepo content
detection works out-of-the-box because all class-emitting code stays inside
`apps/web/`.

### ADR-0006: uv single-project Python (vs uv workspace)

**Status**: Accepted.
**Context**: There is exactly one Python project today (`apps/api`).
Phase 0c will introduce `data/scripts/`, but it is unclear whether that
folder will become a packaged Python project or remain a flat-script
directory. uv supports both single-project and workspace layouts.
**Decision**: Single-project layout. `apps/api/pyproject.toml` is a
self-contained project; `apps/api/uv.lock` lives next to it. Avoid
introducing a root-level `pyproject.toml` that would confuse readers into
thinking there is a top-level Python project.
**Consequences**: If 0c adds a second Python package, we lift to workspace
mode then. Migration is mechanical (move `[tool.uv.workspace]` to root, add
member globs).

### ADR-0007: Pre-commit hooks deferred (CI-only enforcement)

**Status**: Accepted.
**Context**: Local pre-commit hooks (via the `pre-commit` framework, lefthook,
or husky+lint-staged) catch issues before push but add friction for
first-time contributors and need install-time bootstrap.
**Decision**: No `.pre-commit-config.yaml` in 0b. CI gates (`web.yml`,
`api.yml`) are the single source of truth for lint/format/type enforcement.
Document the option in `CONTRIBUTING.md` as a future addition.
**Consequences**: PRs may need lint-fix push-backs. Acceptable cost for a
small team. If contributor velocity demands hooks later, adding the
framework is mechanical.

### ADR-0008: Playwright manual-trigger only

**Status**: Accepted.
**Context**: Playwright browser binaries (~150MB) plus full-app boot consume
GitHub Actions minutes that are scarce on the free tier. The smoke test is
valuable but does not need to run on every PR.
**Decision**: Ship `apps/web/playwright.config.ts` and one smoke spec
(`apps/web/e2e/home.spec.ts`). A dedicated `.github/workflows/e2e.yml`
triggers exclusively on `workflow_dispatch`. No `pull_request` or `push`
triggers anywhere reference Playwright.
**Consequences**: Maintainers must remember to dispatch e2e before tagged
releases. Acceptable for a project at 0b scope.

### ADR-0009: pgvector pinned to `pg16` (Neon parity)

**Status**: Accepted.
**Context**: pgvector publishes `pg18-trixie` as the current image tag.
Neon Postgres production runs PG16/17. Mirroring Neon's major in local-dev
catches version-specific issues (e.g., extension behavior, system catalog
changes) before they hit prod.
**Decision**: Pin `pgvector/pgvector:pg16` in `docker-compose.yml`. Add an
inline comment explaining the Neon-parity rationale. Bump in lockstep with
Neon, not ahead.
**Consequences**: Local-dev runs PG16 even though pgvector publishes newer.
Document the bump trigger (Neon major upgrade) in CONTRIBUTING.

### ADR-0010: docker-compose dev-only (production via Fly.io + Vercel)

**Status**: Accepted.
**Context**: docker-compose is convenient for local dev but production uses
Vercel for `apps/web` and Fly.io for `apps/api`, with managed Neon Postgres
and Upstash Redis.
**Decision**: `docker-compose.yml` declares only `postgres` and `redis` —
the two services that have managed cloud equivalents and need local stand-ins.
No web/api services in compose. The `apps/api/Dockerfile` exists for the
Fly.io deploy path, not for compose.
**Consequences**: Contributors run `just dev` (pnpm + uvicorn natively) plus
`just db-up` (compose for postgres/redis). Two-process model — documented
in CONTRIBUTING.

## Cross-cutting Concerns

### Permitted-paths widening for Phase 0c

The 0b delta to `repo-skeleton` enumerates the permitted application/tooling
paths: `apps/web/**`, `apps/api/**`, `.github/workflows/**`, repo-root
`docker-compose.yml`, repo-root `justfile`. Phase 0c will need at least:

- `data/scripts/*.py` (ingestion + maintenance scripts)
- `apps/api/migrations/**` (Alembic migrations)
- `packages/ontology/**` (taxonomy data files; format TBD — likely YAML/JSON,
  possibly a small Python package)

**Recommendation**: Do NOT widen now. 0b's delta is correct for what 0b
actually adds. 0c will ship its own delta to `repo-skeleton` listing the
data/scripts and migrations paths it needs. Documented here so the 0c
exploration knows to expect it.

### CI cache strategy

- **pnpm**: `pnpm/action-setup@v4` followed by `actions/setup-node@v4` with
  `cache: 'pnpm'`. Cache key derives from `pnpm-lock.yaml`.
- **uv**: `astral-sh/setup-uv@<sha> # v8.1.0` with `enable-cache: true` and
  `cache-dependency-glob: "**/uv.lock"`. Caches uv install + downloaded
  wheels.
- **Playwright**: Not cached in 0b (e2e workflow is manual-only and runs
  rarely). When/if Playwright moves to PR-trigger, add an `actions/cache`
  step keyed on `~/.cache/ms-playwright` and the Playwright version.
- All third-party actions pinned to SHA where Context7 documents the SHA
  (specifically `setup-uv`); first-party `actions/*` use major-version tags
  per GitHub's recommendation.

### Healthcheck convention

`/healthz` (Kubernetes liveness convention) returns `{"status": "ok"}` and
MUST NOT touch DB or Redis at this phase — it is purely a liveness signal
proving the process is up and the event loop is responsive. A separate
`/readyz` for deep-readiness checks (DB ping, Redis ping) lands in 0c when
those connections exist. Choosing `/healthz` over `/health` matches Fly.io's
default health-check path docs and the broader k8s ecosystem.

## File Templates

### `apps/web/package.json`

```json
{
  "name": "web",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "next": "^16.2.2",
    "next-themes": "^0.4.4",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "sonner": "^1.7.0",
    "lucide-react": "^0.460.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.4"
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0",
    "@tailwindcss/postcss": "^4.0.0",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.1.0",
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "eslint": "^9.17.0",
    "eslint-config-next": "^16.2.2",
    "eslint-config-prettier": "^9.1.0",
    "jsdom": "^25.0.1",
    "postcss": "^8.5.0",
    "prettier": "^3.4.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.0",
    "vite-tsconfig-paths": "^5.1.0",
    "vitest": "^3.2.4"
  }
}
```

### `apps/web/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    ".next/types/**/*.ts"
  ],
  "exclude": ["node_modules", ".next", "playwright-report", "test-results"]
}
```

### `apps/web/next.config.ts`

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // No transpilePackages: 0b has no shared workspace packages emitting code into web.
};

export default nextConfig;
```

### `apps/web/postcss.config.mjs`

```js
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

### `apps/web/app/globals.css`

```css
@import "tailwindcss";

/*
 * Tailwind v4 is CSS-first. Theme tokens go in @theme blocks below as the
 * design system grows. shadcn primitives generate their own CSS variables
 * via the `add` command.
 */
```

### `apps/web/app/layout.tsx`

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Fragwise",
  description: "Open-source fragrance discovery with an AI chatbot guide.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
```

### `apps/web/app/page.tsx`

```tsx
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-5xl font-semibold tracking-tight">Fragwise</h1>
      <p className="text-muted-foreground">
        Open-source fragrance discovery with an AI chatbot guide.
      </p>
      <Button disabled>Coming soon</Button>
    </main>
  );
}
```

### `apps/web/components/theme-provider.tsx`

```tsx
"use client";

import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
```

### `apps/web/lib/utils.ts`

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### `apps/web/components.json`

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

### shadcn primitives (do not paste — run CLI)

After `apps/web/package.json`, `tsconfig.json`, `components.json`, and the
empty `app/`, `components/`, `lib/` directories exist, run from
`apps/web/`:

```bash
npx shadcn@latest add button card input label dialog sonner dropdown-menu tabs separator badge
```

This writes the 10 primitives into `apps/web/components/ui/<name>.tsx`. Note
that `sonner` replaces the deprecated `toast` primitive (verified via
Context7 on `/shadcn-ui/ui`). The CLI also installs runtime deps it doesn't
already see in `package.json` (e.g., `@radix-ui/react-*` per primitive). Do
NOT pre-list those — the CLI manages them.

### `apps/web/eslint.config.mjs`

```js
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier";

export default [
  ...nextVitals,
  ...nextTs,
  prettier,
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "playwright-report/**",
      "test-results/**",
      "coverage/**",
    ],
  },
];
```

### Repo-root `.prettierrc`

```json
{
  "semi": true,
  "singleQuote": false,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2
}
```

### `apps/web/vitest.config.ts`

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
  },
});
```

### `apps/web/vitest.setup.ts`

```ts
import "@testing-library/jest-dom/vitest";
```

### `apps/web/__tests__/page.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import HomePage from "@/app/page";

describe("HomePage", () => {
  it("renders the brand name", () => {
    render(<HomePage />);
    expect(
      screen.getByRole("heading", { name: /fragwise/i })
    ).toBeInTheDocument();
  });
});
```

### `apps/web/playwright.config.ts`

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "pnpm next dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
```

### `apps/web/e2e/home.spec.ts`

```ts
import { test, expect } from "@playwright/test";

test("home page renders the Fragwise brand", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /fragwise/i })).toBeVisible();
});
```

### `apps/web/.gitignore`

```gitignore
# next
.next/
out/

# tests
coverage/
playwright-report/
test-results/

# misc
*.tsbuildinfo
next-env.d.ts
```

(The repo-root `.gitignore` already covers `node_modules`, `.env*`, IDE
detritus. Keep this file targeted to web-specific artifacts.)

### `apps/web/next-env.d.ts`

This file is auto-generated by Next on first build. The implementer SHOULD
let `next dev` create it then commit. Do not author by hand.

---

### `apps/api/pyproject.toml`

```toml
[project]
name = "fragwise-api"
version = "0.0.0"
description = "Fragwise FastAPI service with LangGraph agent."
requires-python = ">=3.12,<3.13"
readme = "README.md"
license = { text = "Apache-2.0" }
dependencies = [
    "fastapi>=0.128.0,<1.0",
    "uvicorn[standard]>=0.32,<1.0",
    "langgraph~=1.0.8",
    "httpx>=0.27,<1.0",
    "python-dotenv>=1.0,<2.0",
]

[project.optional-dependencies]
# Empty in 0b. 0c will add `db = ["asyncpg", "sqlalchemy[asyncio]"]` etc.

[dependency-groups]
dev = [
    "ruff>=0.7,<1.0",
    "mypy>=1.13,<2.0",
    "pytest>=8.3,<9.0",
    "pytest-asyncio>=0.24,<1.0",
    "anyio>=4.6,<5.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/fragwise_api"]

[tool.uv]
required-version = ">=0.5"

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "W", "N", "RUF"]
ignore = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src"]
plugins = []

[[tool.mypy.overrides]]
module = ["langgraph.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra --strict-markers"
testpaths = ["tests"]
asyncio_mode = "auto"
```

### `apps/api/.python-version`

```
3.12
```

### `apps/api/src/fragwise_api/__init__.py`

```python
"""Fragwise FastAPI service."""

__version__ = "0.0.0"
```

### `apps/api/src/fragwise_api/main.py`

```python
"""FastAPI app factory + lifespan + /healthz."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hook. Empty in 0b; 0c plugs in DB + Redis here."""
    yield


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application."""
    app = FastAPI(
        title="Fragwise API",
        version="0.0.0",
        lifespan=lifespan,
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        """Liveness probe. MUST NOT touch DB/Redis (separate /readyz arrives in 0c)."""
        return {"status": "ok"}

    return app


app = create_app()
```

### `apps/api/src/fragwise_api/agent.py`

```python
"""LangGraph 1.x stub. Proves install + import shape; no LangChain."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import START, StateGraph


class AgentState(TypedDict):
    text: str


def echo(state: AgentState) -> AgentState:
    """Identity node — replaced in later phases by real chat orchestration."""
    return {"text": state["text"]}


def build_graph() -> StateGraph:  # type: ignore[type-arg]
    graph: StateGraph = StateGraph(AgentState)
    graph.add_node("echo", echo)
    graph.add_edge(START, "echo")
    return graph


compiled = build_graph().compile()
```

### `apps/api/tests/__init__.py`

(Empty file.)

### `apps/api/tests/conftest.py`

```python
"""Pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from fragwise_api.main import app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

### `apps/api/tests/test_health.py`

```python
"""Smoke test for /healthz."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
async def test_healthz_returns_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")
```

### `apps/api/tests/test_no_heavy_ml_deps.py`

```python
"""Regression test: LangGraph install MUST NOT pull torch/transformers."""

from __future__ import annotations

import importlib.util


def test_torch_not_installed() -> None:
    assert importlib.util.find_spec("torch") is None, (
        "torch leaked into the dependency closure — check `uv tree` and prune."
    )


def test_transformers_not_installed() -> None:
    assert importlib.util.find_spec("transformers") is None, (
        "transformers leaked into the dependency closure — check `uv tree` and prune."
    )


def test_sentence_transformers_not_installed() -> None:
    assert importlib.util.find_spec("sentence_transformers") is None, (
        "sentence-transformers leaked in — not allowed in 0b."
    )


def test_langchain_not_installed() -> None:
    assert importlib.util.find_spec("langchain") is None, (
        "langchain leaked in — 0b is langgraph-only."
    )
```

### `apps/api/Dockerfile`

```dockerfile
# syntax=docker/dockerfile:1.7

# ---- builder ------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.5-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_INSTALL_DIR=/python \
    UV_PYTHON_PREFERENCE=only-managed

RUN uv python install 3.12

WORKDIR /app

# Install dependencies first (cache-friendly).
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy project source and install it.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---- runtime ------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# Create unprivileged user
RUN groupadd --system --gid 1001 fragwise \
 && useradd --system --uid 1001 --gid fragwise --home /app fragwise

WORKDIR /app

# Copy uv-managed Python and venv from the builder
COPY --from=builder /python /python
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

USER fragwise

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
  sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

CMD ["uvicorn", "fragwise_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `apps/api/.dockerignore`

```dockerignore
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
coverage.xml
htmlcov/
tests/
.env
.env.*
.python-version
README.md
Dockerfile
.dockerignore
```

---

### `docker-compose.yml` (repo root)

```yaml
# Local-dev infrastructure for Fragwise.
# Production runs on Vercel (web) + Fly.io (api) + Neon (postgres) + Upstash (redis).
# Compose only declares the two managed services that need local stand-ins.

services:
  postgres:
    # Pinned to pg16 to match Neon's production major (Neon parity).
    # Bump in lockstep with Neon, not ahead of it. See ADR-0009.
    image: pgvector/pgvector:pg16
    container_name: fragwise-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: fragwise
      POSTGRES_PASSWORD: fragwise
      POSTGRES_DB: fragwise
    ports:
      - "5432:5432"
    volumes:
      - fragwise-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fragwise -d fragwise"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: fragwise-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - fragwise-redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  fragwise-pgdata:
  fragwise-redisdata:
```

### `justfile` (repo root)

```just
# Fragwise developer recipes. Requires: just, pnpm, uv, docker.

set shell := ["bash", "-cu"]

# Default recipe: list available commands.
default:
    @just --list

# Install both toolchains: pnpm workspace + Python venv via uv.
install:
    pnpm install
    cd apps/api && uv sync

# Run web (3000) + api (8000) concurrently. POSIX-only; Windows users run
# dev-web and dev-api in separate terminals.
dev:
    bash -c 'just dev-web & just dev-api & wait'

# Start the Next.js dev server on port 3000.
dev-web:
    pnpm --filter web dev

# Start the FastAPI dev server on port 8000 with autoreload.
dev-api:
    cd apps/api && uv run uvicorn fragwise_api.main:app --reload --host 127.0.0.1 --port 8000

# Run all tests across the monorepo.
test: test-web test-api

# Run vitest in apps/web.
test-web:
    pnpm --filter web test

# Run pytest in apps/api.
test-api:
    cd apps/api && uv run pytest

# Run all linters and type checkers.
lint: lint-web lint-api

# Lint + typecheck apps/web.
lint-web:
    pnpm --filter web lint
    pnpm --filter web typecheck

# Ruff + mypy strict in apps/api.
lint-api:
    cd apps/api && uv run ruff check .
    cd apps/api && uv run ruff format --check .
    cd apps/api && uv run mypy src

# Bring up postgres + redis detached.
db-up:
    docker compose up -d postgres redis

# Stop and remove postgres + redis containers (volumes preserved).
db-down:
    docker compose down

# Open a psql shell in the running postgres container.
db-shell:
    docker compose exec postgres psql -U fragwise -d fragwise
```

### `.github/workflows/web.yml`

```yaml
name: web

on:
  pull_request:
    paths:
      - "apps/web/**"
      - "package.json"
      - "pnpm-lock.yaml"
      - "pnpm-workspace.yaml"
      - ".github/workflows/web.yml"
  push:
    branches: [main]
    paths:
      - "apps/web/**"
      - "package.json"
      - "pnpm-lock.yaml"
      - "pnpm-workspace.yaml"
      - ".github/workflows/web.yml"

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/web
    steps:
      - uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 10.33.3

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: "pnpm"

      - name: Install workspace
        working-directory: .
        run: pnpm install --frozen-lockfile

      - name: Lint
        run: pnpm lint

      - name: Typecheck
        run: pnpm typecheck

      - name: Test
        run: pnpm test

      - name: Build
        run: pnpm build
```

### `.github/workflows/api.yml`

```yaml
name: api

on:
  pull_request:
    paths:
      - "apps/api/**"
      - ".github/workflows/api.yml"
  push:
    branches: [main]
    paths:
      - "apps/api/**"
      - ".github/workflows/api.yml"

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/api
    steps:
      - uses: actions/checkout@v4

      - name: Setup uv (with cache)
        uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0
        with:
          python-version: "3.12"
          enable-cache: true
          cache-dependency-glob: |
            apps/api/pyproject.toml
            apps/api/uv.lock

      - name: Install dependencies
        run: uv sync --locked

      - name: Ruff lint
        run: uv run ruff check .

      - name: Ruff format check
        run: uv run ruff format --check .

      - name: Mypy strict
        run: uv run mypy src

      - name: Pytest
        run: uv run pytest
```

### `.github/workflows/openspec.yml`

```yaml
name: openspec

on:
  pull_request:

jobs:
  proposal-presence:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Assert every new openspec change has a proposal.md
        shell: bash
        run: |
          set -euo pipefail
          base="${{ github.event.pull_request.base.sha }}"
          head="${{ github.event.pull_request.head.sha }}"
          # Directories under openspec/changes/ touched by this PR (excluding archive).
          changed_dirs=$(git diff --name-only "$base" "$head" \
            | awk -F/ '/^openspec\/changes\/[^/]+\// && $3 != "archive" { print $1"/"$2"/"$3 }' \
            | sort -u)
          if [ -z "$changed_dirs" ]; then
            echo "No openspec changes touched. OK."
            exit 0
          fi
          missing=()
          for d in $changed_dirs; do
            if [ ! -f "$d/proposal.md" ]; then
              missing+=("$d")
            fi
          done
          if [ ${#missing[@]} -gt 0 ]; then
            echo "::error::The following openspec change directories are missing proposal.md:"
            for m in "${missing[@]}"; do
              echo "  - $m"
            done
            exit 1
          fi
          echo "All touched openspec change directories contain proposal.md."
```

### `.github/workflows/e2e.yml`

```yaml
name: e2e

on:
  workflow_dispatch:

jobs:
  playwright:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/web
    steps:
      - uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 10.33.3

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: "pnpm"

      - name: Install workspace
        working-directory: .
        run: pnpm install --frozen-lockfile

      - name: Install Playwright browsers
        run: pnpm exec playwright install --with-deps chromium

      - name: Build
        run: pnpm build

      - name: Run Playwright
        run: pnpm test:e2e
```

---

## Repo-root config updates

### `package.json` (root) — add `scripts`

Modify the existing root `package.json` to add a `scripts` block. Final
content:

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
  "packageManager": "pnpm@10.33.3",
  "scripts": {
    "dev": "pnpm --filter web dev",
    "build": "pnpm --filter web build",
    "lint": "pnpm --filter web lint && pnpm --filter web typecheck",
    "test": "pnpm --filter web test"
  }
}
```

(API-side scripts stay in `justfile`; the root `pnpm` scripts only proxy the
web app since pnpm workspaces don't natively orchestrate Python.)

### `.gitignore` (root) — append section

```gitignore

# 0b additions: per-app build artifacts (per-app .gitignore files exist too).
apps/web/.next/
apps/web/coverage/
apps/web/playwright-report/
apps/web/test-results/
apps/api/.venv/
apps/api/.pytest_cache/
apps/api/.mypy_cache/
apps/api/.ruff_cache/
apps/api/__pycache__/
apps/api/**/__pycache__/
```

**Approach pick**: dual-source — both per-app `.gitignore` (focused) AND
root `.gitignore` (catch-all). Per-app keeps web's `next-env.d.ts` co-located
with the project; root catches anything that escapes to monorepo-wide
operations (e.g., `git status` from root showing missing patterns). Cost is
two lines of duplication, accepted.

### `openspec/config.yaml` — context block

Replace the existing `context:` block contents with:

```yaml
context: |
  Fragwise: open-source fragrance discovery + database with AI chatbot guide.
  Monorepo: apps/web (Next.js 16 + Tailwind v4 + shadcn), apps/api (Python FastAPI + LangGraph 1.x),
  packages/ontology (notes/accords taxonomy), data/ (seed datasets and ingestion scripts).
  Data: Neon Postgres + pgvector (catalog and embeddings), Upstash Redis (cache + rate limit),
  Cloudflare R2 (images). Auth: Clerk. LLM: OpenAI.
  Hosting: Vercel (web) + Fly.io (api) on pay-as-you-go, scale-to-zero machines.
  Self-hostable via docker-compose.
  License: Apache-2.0.
```

The standalone `Hosting:` line that previously appeared after the duplicate
sentence is collapsed into the single canonical clause above.

## Data Flow

Local dev process tree under `just dev`:

    contributor shell
        │
        ├─ just dev-web ─→ pnpm --filter web dev ─→ next dev (3000)
        ├─ just dev-api ─→ uv run uvicorn fragwise_api.main:app (8000)
        └─ just db-up   ─→ docker compose up postgres redis

CI trigger flow on a PR:

    PR opened
        │
        ├─ paths match apps/web/**       ─→ web.yml      (lint, tsc, vitest, build)
        ├─ paths match apps/api/**       ─→ api.yml      (ruff, mypy, pytest)
        ├─ always                        ─→ openspec.yml (proposal.md presence)
        └─ workflow_dispatch (manual)    ─→ e2e.yml      (Playwright smoke)

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `apps/web/package.json` | Create | Next 16 + React 19 + Tailwind v4 + vitest + Playwright manifest |
| `apps/web/tsconfig.json` | Create | Strict TS, `@/*` path alias |
| `apps/web/next.config.ts` | Create | Minimal Next config |
| `apps/web/postcss.config.mjs` | Create | Tailwind v4 PostCSS plugin |
| `apps/web/app/globals.css` | Create | `@import "tailwindcss";` |
| `apps/web/app/layout.tsx` | Create | Root layout + ThemeProvider + Toaster |
| `apps/web/app/page.tsx` | Create | "Fragwise" heading + Coming-soon button |
| `apps/web/components/theme-provider.tsx` | Create | next-themes wrapper |
| `apps/web/components/ui/*.tsx` | Create | 10 shadcn primitives via `shadcn add` |
| `apps/web/lib/utils.ts` | Create | `cn` helper |
| `apps/web/components.json` | Create | shadcn config |
| `apps/web/eslint.config.mjs` | Create | Flat config, Next + Prettier integration |
| `apps/web/vitest.config.ts` | Create | jsdom + tsconfig-paths |
| `apps/web/vitest.setup.ts` | Create | jest-dom matchers |
| `apps/web/__tests__/page.test.tsx` | Create | Smoke render test |
| `apps/web/playwright.config.ts` | Create | Chromium + webServer |
| `apps/web/e2e/home.spec.ts` | Create | Asserts "Fragwise" on `/` |
| `apps/web/.gitignore` | Create | `.next/`, coverage, reports |
| `apps/web/.gitkeep` | Delete | No longer empty |
| `apps/api/pyproject.toml` | Create | uv single-project, ruff/mypy/pytest config |
| `apps/api/uv.lock` | Create | Generated by `uv sync` |
| `apps/api/.python-version` | Create | `3.12` |
| `apps/api/src/fragwise_api/__init__.py` | Create | Package marker + version |
| `apps/api/src/fragwise_api/main.py` | Create | App factory + lifespan + `/healthz` |
| `apps/api/src/fragwise_api/agent.py` | Create | LangGraph 1.x stub |
| `apps/api/tests/__init__.py` | Create | Empty |
| `apps/api/tests/conftest.py` | Create | `httpx.AsyncClient` fixture |
| `apps/api/tests/test_health.py` | Create | `/healthz` smoke test |
| `apps/api/tests/test_no_heavy_ml_deps.py` | Create | Asserts torch/transformers absent |
| `apps/api/Dockerfile` | Create | Multi-stage uv → python:3.12-slim |
| `apps/api/.dockerignore` | Create | Excludes venv, caches, tests |
| `apps/api/.gitkeep` | Delete | No longer empty |
| `docker-compose.yml` | Create | postgres pg16 + redis 7-alpine |
| `justfile` | Create | 14 recipes |
| `.github/workflows/web.yml` | Create | Lint+tsc+vitest+build |
| `.github/workflows/api.yml` | Create | Ruff+mypy+pytest |
| `.github/workflows/openspec.yml` | Create | proposal.md presence check |
| `.github/workflows/e2e.yml` | Create | Manual Playwright |
| `.prettierrc` | Create | Repo-root Prettier config |
| `package.json` (root) | Modify | Add `scripts` block |
| `.gitignore` (root) | Modify | Append per-app artifact ignores |
| `openspec/config.yaml` | Modify | Update `context:` to Next 16 + Tailwind v4 + LangGraph 1.x |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit (web) | `<HomePage />` renders "Fragwise" | vitest + @testing-library/react |
| Unit (api) | `/healthz` returns 200 + `{"status":"ok"}` | pytest + httpx.AsyncClient |
| Static (api) | torch/transformers/sentence-transformers/langchain absent | `importlib.util.find_spec` regression test |
| Lint/Type (web) | ESLint flat + `tsc --noEmit` | `pnpm lint` + `pnpm typecheck` |
| Lint/Type (api) | ruff check, ruff format --check, mypy strict | `uv run ...` per recipe |
| E2E (web) | Smoke: home page renders "Fragwise" | Playwright, chromium-only, manual dispatch |
| Build (web) | `next build` succeeds | CI step in web.yml |
| Build (api) | `docker build apps/api` succeeds + image serves /healthz | NOT in 0b CI; verified locally during sdd-verify |

## Migration / Rollout

No data migration. Pre-merge revert: `git reset` the change branch.
Post-merge revert: revert the merge commit. The change is purely additive
plus one `openspec/config.yaml` string edit.

## Open Questions

None. All exploration Q1–Q10 ratified by the user prior to `sdd-spec`.
Verified library state via Context7 on 2026-05-06.

---

## Return Envelope

**Status**: success
**Summary**: Design complete for `phase-0b-app-tooling-and-docker`. All file
templates are paste-ready; all version pins verified via Context7 on
2026-05-06 (Next 16.2.2 + React 19 + Tailwind v4, FastAPI 0.128, LangGraph
1.0.8, uv 0.5+, Python 3.12-slim-bookworm, pgvector pg16, redis 7-alpine,
setup-uv v8.1.0 SHA-pinned). Six new ADRs (0005–0010). Repo-skeleton
permitted-paths widening intentionally not extended for 0c — that delta is
0c's responsibility and is documented in cross-cutting concerns.
**Artifacts**:
- `openspec/changes/phase-0b-app-tooling-and-docker/design.md`
**Next recommended**: `sdd-tasks` for `phase-0b-app-tooling-and-docker`.
**Risks**: Tailwind v4 monorepo content scan (W-R1) — mitigated by keeping
class-emitting code inside `apps/web/`. LangGraph 1.0 dep churn (A-R2) and
heavy-ML transitive leak (A-R3) — mitigated by tight pin (`~=1.0.8`) and
the `test_no_heavy_ml_deps.py` regression test that the api workflow
runs every PR. pgvector tag drift (I-R1) — mitigated by ADR-0009 + inline
compose comment. CI path-filter blind spots (I-R2) — mitigated by including
the workflow file itself + `pnpm-workspace.yaml` + `pnpm-lock.yaml` in
filter lists. Playwright minute budget (W-R-Playwright) — eliminated by
`workflow_dispatch`-only `e2e.yml`.
