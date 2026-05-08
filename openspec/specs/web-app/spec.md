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

`apps/web/app/(site)/page.tsx` MUST render the literal string "Fragwise" as primary heading content using the display font, alongside the new home structure: a hero section with a one-line tagline, a "discover by mood" tile grid (links MUST resolve to 200 in 4a, either via 4b routes or via `/fragrances?accord=<slug>` filtered fallback), a "featured fragrances" strip with at least four `FragranceCard` instances populated from the live API, a "from the journal" placeholder teaser, and the site footer.

#### Scenario: Home renders the brand name

- GIVEN the dev server is running
- WHEN a client requests `GET /`
- THEN the rendered HTML contains the string "Fragwise"
- AND the response status is 200

#### Scenario: Home renders hero, featured strip, and footer

- GIVEN the dev server is running with the API reachable
- WHEN a client requests `GET /`
- THEN the rendered HTML contains hero tagline copy
- AND it contains at least four `FragranceCard` instances under a "featured fragrances" heading
- AND it contains a footer with GitHub, License, and Contributing links

### Requirement: API Client Wired And Typed

The web app MUST consume the API through a typed client generated from `apps/api/openapi.json`. `openapi-typescript` MUST be installed as a devDependency, `openapi-fetch` MUST be a runtime dependency, and a `pnpm generate-api-types` script (wired via `predev` and `prebuild`) MUST regenerate `apps/web/lib/api/types.ts`. CI MUST fail if the committed `types.ts` is stale relative to `openapi.json`.

#### Scenario: Generation script and CI gate present

- GIVEN `apps/web/package.json`
- WHEN inspecting `scripts`
- THEN `generate-api-types`, `predev`, and `prebuild` entries exist and run the generation step
- AND CI fails when `git diff --exit-code apps/web/lib/api/types.ts` is non-empty after regenerating

#### Scenario: Typed client used by server components

- GIVEN any server component fetching catalog data
- WHEN it imports the client
- THEN it imports from `apps/web/lib/api/client.ts` (the typed `openapi-fetch` instance)
- AND no untyped `fetch(API_URL + '/...')` call exists in the catalog routes

### Requirement: Light Theme Tokens And Display Fonts

The web app MUST ship a light-only token palette (color, spacing, radii, shadows, type scale) defined as CSS custom properties, and MUST load Fraunces (display), Manrope (sans body), and JetBrains Mono (mono) via `next/font/google`. The previously-imported `Inter` font MUST be removed.

#### Scenario: Tokens and fonts in place; Inter removed

- GIVEN `apps/web/app/layout.tsx` and the token CSS file
- WHEN inspecting them
- THEN the three fonts are imported from `next/font/google` with `display: 'swap'` and exposed as CSS variables
- AND `:root` defines the color, spacing, radii, shadows, and type-scale tokens
- AND `Inter` is no longer imported

### Requirement: Image Fallback For Missing Images

Every place the catalog renders a fragrance image MUST use a shared component that falls back to a deterministic colored panel with a centered first-letter glyph when no `image_url` is available. No broken-image icon MAY be visible to end users for image-less fragrances.

#### Scenario: Missing image renders fallback panel

- GIVEN a fragrance with `image_url === null`
- WHEN any catalog surface (card, detail hero) renders it
- THEN the shared `ImageFallback` component is used
- AND no `<img>` with broken `src` is rendered

### Requirement: Glossary Popovers On Jargon

Long-form catalog copy (detail descriptions, hero metadata strips, journal teasers) MUST wrap recognized jargon terms (approximately 12 seed terms) in the `Glossary` popover component. The popover MUST be triggerable consistently via click, tap, and keyboard activation. Hover-only triggering is NOT required because the underlying Radix `Popover` primitive opens on click/tap rather than hover.

#### Scenario: Recognized term rendered with popover wrapper

- GIVEN body copy on a detail page contains the word "sillage"
- WHEN the page renders
- THEN the term is wrapped by `Glossary` with a dotted underline
- AND a popover with the definition appears on click, tap, or keyboard activation

### Requirement: ISR Caching With Cache Tags

Catalog pages MUST use Next.js Incremental Static Regeneration with the following posture: home `revalidate: 600`, list `revalidate: 300` keyed by `searchParams`, detail `revalidate: 600` with cache tag `fragrance:{slug}`. No catalog page MAY use `export const dynamic = 'force-dynamic'`.

#### Scenario: ISR options match the posture

- GIVEN the home, list, and detail server components
- WHEN inspecting their data fetch options
- THEN home calls pass `next: { revalidate: 600 }`
- AND list calls pass `next: { revalidate: 300 }` with cache key reflecting `searchParams`
- AND detail calls pass `next: { revalidate: 600, tags: ['fragrance:<slug>'] }`

#### Scenario: No force-dynamic exports

- GIVEN any file under `apps/web/app/(site)/`
- WHEN searching for `export const dynamic`
- THEN no occurrence sets the value to `'force-dynamic'`

### Requirement: Sitemap And Robots

`apps/web/app/sitemap.ts` and `apps/web/app/robots.ts` MUST exist and emit a valid sitemap (including all known fragrance slugs at build time) and a robots policy referencing that sitemap.

#### Scenario: Sitemap and robots files present and emit valid output

- GIVEN `next build` has run
- WHEN fetching `/sitemap.xml` and `/robots.txt`
- THEN both endpoints return a 200 with valid content
- AND the sitemap includes `/`, `/fragrances`, and one entry per known fragrance slug
- AND the robots body references the sitemap URL

### Requirement: URL-Driven Pagination

Pagination state for any list page MUST live in the URL `searchParams` (e.g., `?offset=`, `?limit=`), NOT in client component state.

#### Scenario: Page navigation updates URL

- GIVEN a paginated list
- WHEN the user navigates to a different page
- THEN the URL `searchParams` reflect the new offset
- AND the page is rerendered as a server component reading those params

### Requirement: Site Layout With Header, Footer, Drawer, Skip-To-Content

`apps/web/app/(site)/layout.tsx` MUST render the `Header` (with disabled search input), the `Footer`, a mobile `sheet` drawer for navigation, and a `SkipToContent` link as the first focusable element targeting `#main-content`.

#### Scenario: Layout structure present

- GIVEN any page under the `(site)` route group
- WHEN the page renders
- THEN the DOM contains the skip link, header, main content with `id="main-content"`, and footer
- AND on viewports `<md` the nav opens via the sheet drawer
