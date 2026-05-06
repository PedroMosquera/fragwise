# web-app Specification

## Purpose

Defines the Next.js 16 web application scaffold at `apps/web/`: App Router layout, Tailwind v4 styling, shadcn primitives, TypeScript strict mode, ESLint flat config, Prettier, and the vitest + Playwright test toolchain. No domain logic — only the toolchain and a smoke home page.

## Requirements

### Requirement: Next.js 16 App Router Scaffold

`apps/web/` MUST contain a Next.js 16 App Router project. `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, and `apps/web/next.config.ts` (or `.mjs`) MUST exist. `apps/web/package.json` MUST pin `next` to a `^16` range.

#### Scenario: App Router files present and Next pinned to 16

- GIVEN `apps/web/`
- WHEN inspecting the directory and `package.json`
- THEN `app/layout.tsx`, `app/page.tsx`, and `next.config.{ts,mjs}` are tracked
- AND `dependencies.next` matches `^16`

### Requirement: TypeScript Strict Mode

`apps/web/tsconfig.json` MUST set `"strict": true` and MUST extend a Next.js boilerplate base (`next/core-web-vitals` or shipped `tsconfig` from the Next 16 template).

#### Scenario: tsconfig is strict

- GIVEN `apps/web/tsconfig.json`
- WHEN parsing it as JSON
- THEN `compilerOptions.strict` is `true`
- AND `tsc --noEmit` exits 0 against the scaffolded source

### Requirement: Tailwind v4 PostCSS Configuration

`apps/web/postcss.config.{js,mjs}` MUST configure the `@tailwindcss/postcss` plugin. `apps/web/app/globals.css` MUST import Tailwind v4 via the v4 import directive (`@import "tailwindcss";` or the current shipped equivalent). No `tailwind.config.{ts,js}` file MAY be committed (v4 is CSS-first).

#### Scenario: Tailwind v4 wired without JS config

- GIVEN `apps/web/`
- WHEN inspecting PostCSS, CSS, and config files
- THEN `postcss.config.{js,mjs}` references `@tailwindcss/postcss`
- AND `app/globals.css` contains the v4 Tailwind import directive
- AND no `tailwind.config.ts` or `tailwind.config.js` exists

### Requirement: shadcn Primitive Set Installed

The shadcn primitives `button`, `card`, `input`, `label`, `dialog`, `sonner` (toast), `dropdown-menu`, `tabs`, `separator`, and `badge` MUST each be present at `apps/web/components/ui/<name>.tsx`. `apps/web/components.json` MUST exist.

#### Scenario: All starter primitives are present

- GIVEN `apps/web/components/ui/`
- WHEN listing the directory
- THEN one `.tsx` file exists per required primitive
- AND `apps/web/components.json` is tracked by git

### Requirement: Theme Provider Wired In Layout

`apps/web/components/theme-provider.tsx` (or current shadcn convention) MUST exist and MUST be rendered as a wrapper inside `app/layout.tsx`.

#### Scenario: ThemeProvider wraps the app

- GIVEN `apps/web/app/layout.tsx`
- WHEN reading the file
- THEN it imports the theme provider from `components/theme-provider`
- AND the provider wraps `{children}` inside `<body>`

### Requirement: Vitest Unit Test Toolchain

`apps/web/vitest.config.{ts,mjs}` MUST exist with `jsdom` environment and tsconfig path-alias resolution. At least one passing test MUST exist (e.g., a render test for the home page). `pnpm --filter web test` MUST exit 0.

#### Scenario: Vitest runs and at least one test passes

- GIVEN `apps/web/`
- WHEN running `pnpm --filter web test`
- THEN the runner discovers at least one test
- AND every test passes
- AND the process exits 0

### Requirement: Playwright Smoke Test Configured (Manual Trigger Only)

`apps/web/playwright.config.ts` MUST exist. `apps/web/e2e/home.spec.ts` MUST navigate to `/` and assert the string "Fragwise" is visible. Playwright MUST NOT run on push/PR CI; it runs only via `workflow_dispatch`.

#### Scenario: Smoke spec asserts brand on the home page

- GIVEN a running dev server on port 3000
- WHEN Playwright executes `e2e/home.spec.ts`
- THEN the test navigates to `/`
- AND asserts the text "Fragwise" is visible
- AND no Playwright job is invoked from `pull_request` or `push` triggers in any workflow

### Requirement: ESLint Flat Config and Prettier

`apps/web/eslint.config.{js,mjs}` (flat config from `eslint-config-next`) MUST exist. A Prettier config (`.prettierrc*` or `prettier.config.*`) MUST exist at the repo root or `apps/web/`. `pnpm --filter web lint` MUST exit 0 against the scaffolded source.

#### Scenario: Lint passes on scaffold

- GIVEN `apps/web/`
- WHEN running `pnpm --filter web lint`
- THEN ESLint reports zero errors
- AND the process exits 0

### Requirement: Web Package Manifest

`apps/web/package.json` MUST declare these dependencies (any version range): `next`, `react`, `react-dom`, `tailwindcss`, `typescript`, `vitest`, `@testing-library/react`, `@playwright/test`, `eslint`, `prettier`. It MUST declare scripts `dev`, `build`, `start`, `lint`, `test`, `test:e2e`, and `typecheck`.

#### Scenario: Required deps and scripts declared

- GIVEN `apps/web/package.json`
- WHEN parsing it as JSON
- THEN every required dependency name appears in `dependencies` or `devDependencies`
- AND every required script name appears under `scripts` and is non-empty

### Requirement: Brand Visible On Home Page

`apps/web/app/page.tsx` MUST render the literal string "Fragwise" as primary heading content and MAY include a placeholder tagline. No real product UI is in scope.

#### Scenario: Home renders the brand name

- GIVEN the dev server is running
- WHEN a client requests `GET /`
- THEN the rendered HTML contains the string "Fragwise"
- AND the response status is 200
