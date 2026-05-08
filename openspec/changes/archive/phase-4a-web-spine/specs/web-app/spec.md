# Delta for web-app

## ADDED Requirements

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

### Requirement: Glossary Tooltips On Jargon

Long-form catalog copy (detail descriptions, hero metadata strips, journal teasers) MUST wrap recognized jargon terms (approximately 12 seed terms) in the `Glossary` tooltip component. The tooltip MUST be triggerable by hover, keyboard focus, and touch.

#### Scenario: Recognized term rendered with tooltip wrapper

- GIVEN body copy on a detail page contains the word "sillage"
- WHEN the page renders
- THEN the term is wrapped by `Glossary` with a dotted underline
- AND a tooltip with the definition appears on hover, focus, and tap

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

## MODIFIED Requirements

### Requirement: Brand Visible On Home Page

`apps/web/app/(site)/page.tsx` MUST render the literal string "Fragwise" as primary heading content using the display font, alongside the new home structure: a hero section with a one-line tagline, a "discover by mood" tile grid (links MAY 404 until Phase 4b), a "featured fragrances" strip with at least four `FragranceCard` instances populated from the live API, a "from the journal" placeholder teaser, and the site footer.
(Previously: home rendered only "Fragwise" plus an optional placeholder tagline; no real product UI was in scope. 4a graduates the home page from scaffold to the catalog spine's entry point.)

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
