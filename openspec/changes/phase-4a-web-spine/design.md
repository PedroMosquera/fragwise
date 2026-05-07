# Design: Phase 4a — Web Spine

## Process Gates (read first)

> **`judgment-day` adversarial review status: ESCALATED-WITH-CARVEOUTS
> after 2 fix iterations** (Rounds 1, 2 + R3 surgical inline fixes).
> 3 CRITICALs from R3 fixed surgically (wrapGlossary regex Unicode
> boundaries + bare-key aliases; sitemap loop upper-bound guard;
> duplicate `color-scheme` meta tag eliminated). Smaller R3 warnings
> documented as "Known Follow-ups for Apply Phase" (F1-F13 below).
> Apply phase is responsible for verifying each F-item against running
> code (`next build`, `next dev`, `vitest`, Playwright). The orchestrator
> chose this path over Round 4 because the remaining issues need
> runtime verification that static review cannot provide.

> **`frontend-design` skill output is captured in ADR-0033.** The skill
> guidance was applied during this design pass, not during exploration
> or proposal. The aesthetic direction below is the locked output of
> that pass.

## Technical Approach

Phase 4a graduates `apps/web/` from the P0b scaffold to a working catalog
UI with three load-bearing pages: home (`/`), fragrance list
(`/fragrances`), and fragrance detail (`/fragrances/[slug]`). All data
flows through React Server Components calling a typed `openapi-fetch`
client that consumes the now-locked `apps/api/openapi.json` contract.
Filter and pagination state lives in URL `searchParams` (Next.js 16's
async props API). Caching is ISR-by-default (no `force-dynamic`) with
cache tags ready for P5 admin-driven revalidation.

Aesthetic direction is **editorial perfumery** (ADR-0033): Fraunces
display, Manrope body, JetBrains Mono technical labels, ivory/ink/sepia
palette, asymmetric magazine layouts, and a deterministic
`ImageFallback` panel that reads as intentional rather than broken.

The 13-route phase-4 surface is split: 4a ships the spine (3 pages +
shell + design system + API client + glossary + sitemap), 4b ships
taxonomy/people pages (notes/accords/brands/perfumers/articles). Internal
links from 4a to 4b targets render as non-interactive placeholders or
fall back to filtered list URLs (e.g. `/fragrances?accord=woody`) which
DO exist in 4a.

## Architecture Decisions (ADR Index)

| # | Title | Choice |
|---|---|---|
| 0033 | Editorial-perfumery aesthetic direction | Frontend-design skill output: ivory/ink/sepia palette, Fraunces+Manrope+JetBrains Mono, asymmetric magazine layouts |
| 0034 | Typed API client | `openapi-typescript` (devDep) + `openapi-fetch` (runtime); skip TanStack Query in 4a |
| 0035 | ISR posture | RSC fetches with `next: { revalidate, tags }`; no `force-dynamic` |
| 0036 | ImageFallback hash algorithm | SHA-256(slug) → first 4 hex bytes → HSL(hue, 38%, 72%) panel |
| 0037 | Light theme only in 4a | `forcedTheme="light"` on `next-themes`; toggle deferred to 4b |
| 0038 | shadcn primitive set additions | 10 primitives via single `shadcn add` invocation |
| 0039 | Glossary tooltip pattern | shadcn `tooltip` wrapper; ~12 seed terms in static module |
| 0040 | Sitemap and robots | Build-time API fetch in `app/sitemap.ts`; `app/robots.ts` references it |

### ADR-0033: Editorial-perfumery aesthetic direction

**Choice**: Editorial-perfumery direction — a magazine-cover feel rather
than SaaS-landing. Captured from a direct invocation of the
`frontend-design` skill during this design pass.

**Pillars (locked):**
- **Conceptual tone**: refined, warm, slow. Connoisseur AND beginner
  feel welcomed. Negative space is treated as a first-class element.
  Asymmetry over centred grids on hero compositions.
- **Typography**:
  - Display: **Fraunces** (variable, weight 400/500/600). Used for
    page titles, fragrance names on detail pages, the brand wordmark,
    and the centered glyph inside `ImageFallback`. `font-style: italic`
    is reserved for editorial pull-quotes; tracking tightened on large
    sizes (`tracking-tight`).
  - Body: **Manrope** (weight 400/500/600/700). Used for paragraph
    text, navigation, buttons, and card copy. `letter-spacing` neutral.
  - Mono: **JetBrains Mono** (weight 400/500). Used for technical
    labels: year, concentration code (EDP/EDT), gender code, slugs in
    metadata strips, breadcrumbs separators.
- **Palette** (light only — see ADR-0037):
  - `--color-background`: `oklch(0.985 0.005 90)` (ivory-paper)
  - `--color-card`: `oklch(0.99 0.003 90)` (off-white card surface)
  - `--color-foreground`: `oklch(0.21 0.025 270)` (deep ink, blue-black,
    not pure black)
  - `--color-muted-foreground`: `oklch(0.46 0.02 270)`
  - `--color-muted`: `oklch(0.95 0.008 90)`
  - `--color-border`: `oklch(0.90 0.008 90)`
  - `--color-primary`: `oklch(0.30 0.05 35)` (sepia-ink — used sparingly
    for primary CTA, focus rings)
  - `--color-primary-foreground`: `oklch(0.985 0.005 90)`
  - `--color-secondary`: `oklch(0.94 0.012 70)` (parchment)
  - `--color-secondary-foreground`: `oklch(0.21 0.025 270)`
  - `--color-accent`: `oklch(0.62 0.12 30)` (warm terracotta — single
    accent, never overused; reserved for hover states + chip selection
    + glossary underlines)
  - `--color-accent-foreground`: `oklch(0.985 0.005 90)`
  - `--color-ring`: `oklch(0.62 0.12 30)`
- **Spacing rhythm**: 4px base (`--space-1: 0.25rem`) up to 96px
  (`--space-24`). Hero blocks use `--space-16` / `--space-24` of
  vertical breathing.
- **Radii**: card `--radius-md: 0.5rem`, button `--radius-sm: 0.375rem`,
  pill chip `--radius-full: 9999px`.
- **Shadows**: deliberately soft. `--shadow-sm: 0 1px 2px oklch(0.21
  0.025 270 / 0.04)`; `--shadow-md: 0 4px 12px oklch(0.21 0.025 270 /
  0.06)`. No glow, no neon.
- **Motion**: CSS-only; one orchestrated entrance on `/` (staggered
  fade-up of hero → featured strip via `animation-delay`); 150ms
  card hover (`translateY(-2px)` + shadow-md). No `framer-motion` /
  `motion` dep.
- **Composition signatures** (the "unforgettable" detail):
  - Home hero: large Fraunces display string set off-grid against a
    parchment block; asymmetric editorial layout.
  - Fragrance card: brand name in JetBrains Mono micro-caps above a
    Fraunces fragrance name (mirrors print magazine bylines).
  - Notes pyramid: three rows labelled in mono (`TOP / HEART / BASE`),
    note names in Manrope, an accord-tinted vertical rule on the left
    edge.
  - Image fallback: deterministic warm hue (sepia/terracotta/sage band
    via hash) with the first letter set in Fraunces 600 at 25% panel
    height, off-centre.

**Alternatives considered**:
- Modernist apothecary (geometric sans, low-chroma earth) — rejected as
  too cold for fragrance subject matter.
- Minimal Swiss / single-sans — rejected as too generic; high risk of
  the "AI slop" outcome the user explicitly named.

**Rationale**: Direction matches the user's stated "warm, editorial,
refined" framing, embraces the `frontend-design` skill's BOLD-direction
guidance, and gives the catalog visual identity that survives the
image-less common case (most seeded fragrances have no R2 image — see
ADR-0036).

**Bundle budget enforcement (revised under judgment-day)**: the design
locks a 220 KB gzipped initial-JS budget per surface (`/`,
`/fragrances`), enforced by `size-limit` in CI rather than by a manual
self-check. The Radix peer-dep weight makes 200 KB unrealistic; 220 KB
keeps drift small while staying achievable. The mobile-menu sheet is
lazy-imported to keep above-the-fold JS lean. See "Cross-Cutting
Concerns / Bundle budget" for the size-limit config and CI step.

### ADR-0034: openapi-typescript + openapi-fetch (no TanStack Query)

**Choice**: `openapi-typescript@7.x` (devDep, codegen) + `openapi-fetch`
(runtime, ~6 KB gzipped). Skip TanStack Query in 4a.

**Alternatives considered**:
- `hey-api/openapi-ts` (heavier SDK codegen) — rejected, harder to
  tree-shake, more opinionated.
- `openapi-typescript` only + hand-written `fetch` wrapper — rejected,
  ~50 LOC of boilerplate per use site without typed `data | error`
  branches.
- TanStack Query — rejected, adds ~16 KB gzipped + provider boilerplate
  for zero current benefit (no writes in 4a; filters are URL-driven and
  RSC-rerendered).

**Rationale**: `createClient<paths>({ baseUrl, fetch })` returns
discriminated `data | error` unions, forces 4xx handling at the call
site, and Context7 docs confirm the per-call init object passes
through to native `fetch` — Next.js's `next: { revalidate, tags }`
extensions ride along unchanged. CI gate (regen + `git diff
--exit-code`) prevents stale committed types.

### ADR-0035: ISR-by-default with cache tags

**Choice**: All catalog routes use Next.js `fetch` with
`next: { revalidate, tags }`. No `export const dynamic = 'force-dynamic'`.
No `force-static` either (so on-demand revalidation stays available).

| Route | revalidate | tags |
|---|---|---|
| `/` | 600 | `featured`, `journal` |
| `/fragrances` | 300 (key includes `searchParams`) | `fragrances:list` |
| `/fragrances/[slug]` | 600 | `fragrance:{slug}` |
| `app/sitemap.ts` | 3600 (build + hourly) | `sitemap` |

**Alternatives considered**:
- `cache: 'force-cache'` with on-demand invalidation only — rejected,
  no fallback if a tag-purge is missed.
- `force-dynamic` — rejected, kills the cache layer P1 already ships
  (`Cache-Control: public, max-age=60, stale-while-revalidate=300`).

**Rationale**: Tags let P5 admin tooling purge specific fragrance pages
on edit without reshipping. ISR windows are short enough that staleness
is bounded.

### ADR-0036: ImageFallback hash algorithm

**Choice**: Deterministic `slug → oklch` mapping using SHA-256, with
**constant perceived lightness** (`L=0.78`) and dark ink universally.

```ts
// apps/web/components/catalog/ImageFallback.tsx (excerpt)
import { createHash } from "node:crypto";
// runs in RSC — node:crypto is fine on the Node runtime tier.

const BANDS = [25, 35, 45, 70, 200, 280];

function panelOklch(slug: string): { bg: string; fg: string } {
  const h = createHash("sha256").update(slug).digest("hex");
  const band = parseInt(h.slice(0, 2), 16) % 6;
  const jitterByte = parseInt(h.slice(2, 4), 16);
  const jitter = (jitterByte % 12) - 6;
  const hue = BANDS[band] + jitter;
  return {
    bg: `oklch(0.78 0.06 ${hue})`,
    fg: "var(--color-foreground)", // dark ink — passes AA on all 6 bands
  };
}
```

**Why oklch + constant L (revised under judgment-day)**: the original
draft used HSL `(h, 38%, 72%)`. HSL lightness 72 maps to very
different *perceived* lightnesses across hues — yellow-green panels
read much lighter than dusk-blue panels at the same L value. Ivory
text on the four lighter HSL bands fails WCAG AA. oklch is
perceptually uniform: at `L=0.78` every band has the same perceived
lightness, so a single dark-ink foreground passes AA everywhere and we
no longer need a hue-dependent fg branch.

**Determinism guarantee**: same `slug` ALWAYS produces identical
`bg` + `fg` strings. Algorithm is documented in this ADR and asserted
in `__tests__/ImageFallback.test.tsx`.

**Detail-page hero variant (S6)**: on `/fragrances/[slug]`, the hero
slot uses an editorial **typographic-only** fallback (large Fraunces
fragrance name + brand wordmark over the same oklch panel), not the
small-letter-bottom-corner pattern used by cards. See the detail
page snippet for the hero JSX.

**Alternatives considered**:
- `djb2`/`fnv1a` (cheaper hash) — rejected, SHA-256 is already on the
  Node runtime via `node:crypto`; bundle-free; collisions don't matter
  for visual hashing.
- HSL `(h, 38%, 72%)` (original draft) — rejected, contrast fails AA
  on 4 of 6 bands due to non-uniform perceived lightness.
- Pure-typographic card (no panel) — rejected, fragrance cards then
  visually collide with article cards in the same grid.
- CSS bottle silhouette — rejected, looks like a placeholder.

**Edge runtime note**: `node:crypto` is the Node-runtime API. If any
`(site)` route is later migrated to Edge runtime, swap `createHash` for
an async `crypto.subtle.digest("SHA-256", ...)` wrapper. We do NOT pin
Edge runtime today, so the sync hash is correct.

**Rationale**: Cheap, no extra dep, intentional-looking, palette
cohesion (6 bands, constant L), and provably AA-compliant contrast.

### ADR-0037: Light theme only in 4a

**Choice**: `apps/web/components/theme-provider.tsx` is configured with
`forcedTheme="light"`. No `.dark { ... }` token block ships in 4a. The
theme toggle UI is NOT rendered in `Header`. `next-themes` stays wired
so 4b can land dark with no provider refactor.

**Native widget commitment**: in addition to `forcedTheme`, 4a sets
`color-scheme: light` at `:root` (in `tokens.css`) AND emits the
`Viewport.colorScheme: 'light'` metadata in `app/layout.tsx`. Without
these, OS dark-mode users see dark-themed native widgets — scrollbars,
autofill, disabled `<input type="search">` chrome — sitting on top of
the ivory background. The CSS-only commitment guards against the
`forcedTheme` class arriving after first paint.

**Alternatives considered**:
- Ship light + dark — rejected, naive inversion of an editorial palette
  is "ugly dark mode"; needs a hand-tuned dark palette (4b scope).
- Strip `next-themes` entirely — rejected, would require re-introducing
  the dependency in 4b.

**Rationale**: One palette done right beats two done badly. The user
named "AI slop" as the worst-case outcome; auto-inverted dark mode
qualifies.

### ADR-0038: shadcn primitive set additions (10 components)

**Choice**: A single CLI invocation adds all ten primitives:

```bash
cd apps/web && npx shadcn@latest add sheet tooltip accordion command \
  skeleton popover scroll-area breadcrumb select pagination
```

Verified against Context7 (`/llmstxt/ui_shadcn_llms_txt`): each
component supports `npx shadcn@latest add <name>` and the CLI accepts
multiple component names in one invocation.

After this command runs, `apps/web/components/ui/` contains all 20
required primitive files (10 from P0b + 10 new). Each primitive file
remains hand-editable per shadcn's "open code" model.

**Alternatives considered**:
- Add primitives lazily as pages need them — rejected, makes early
  task ordering noisy and yields multiple small lockfile churn commits.

**Rationale**: One install, one lockfile bump, one PR diff to review.

### ADR-0039: Glossary popover pattern with ~12 seed terms

**Choice**: `apps/web/components/site/Glossary.tsx` is a `"use client"`
wrapper around shadcn **`popover`** (NOT `tooltip`). Term data lives in
`apps/web/lib/glossary.tsx` as a `Record<string, { term, definition }>`
plus a generic `wrapGlossary(text, Glossary)` helper. First mention per
term per page renders as a `<button>` with a dotted underline; tapping
or pressing Enter/Space opens a popover with the definition. Subsequent
mentions render as plain text.

**Why Popover, not Tooltip** (revision under judgment-day): Radix
`Tooltip` fires on hover and keyboard focus only — touch users see the
dotted underline and get no payoff. The spec REQUIRES the trigger to
also work on touch (`fragrance-catalog-ui` Requirement: "Touch users
MUST be able to trigger the tooltip via tap"). Popover is click/tap
+ keyboard, satisfying both requirements. Hover users now tap once
rather than wait on a hover delay — an acceptable trade-off given the
alternative breaks mobile.

**Term selection (12)**: `sillage`, `accord`, `drydown`, `chypre`,
`fougere`, `oriental`, `gourmand`, `aquatic`, `edt`, `edp`, `parfum`,
`top-heart-base`. (`top-heart-base` is one combined term covering the
pyramid roles.) See `apps/web/lib/glossary.tsx` skeleton below.

**Wrapping mechanism**: `wrapGlossary(text, Glossary)` is the canonical
path. It scans `text` for the first occurrence of EACH glossary term
(case-insensitive, word-boundary, longest-alias-first), wraps that
match with `<Glossary>`, and leaves all other text verbatim. The
detail page calls this on `f.description`. The naïve
`description.split(term)` pattern is forbidden — it silently drops
content past the second occurrence and only handles one term out of 12.

**Alternatives considered**:
- shadcn `tooltip` — rejected, no touch trigger (spec violation).
- Inline parenthesised definitions — rejected, breaks editorial flow.

**Rationale**: Cheap to ship (~50 LOC + 12 records + helper),
materially differentiates the beginner experience, satisfies the
spec's touch requirement, and aligns with the dual-audience goal.

### ADR-0040: Sitemap and robots from build-time API fetch

**Choice**: `apps/web/app/sitemap.ts` pages through `getFragrances` at
build time (PAGE=100 — the `limit` parameter on `/api/v1/fragrances`
has `maximum: 100` per `apps/api/openapi.json`; sending 1000 would
422 and fail `next build`). It emits `/`, `/fragrances`, and one entry
per fragrance slug. `apps/web/app/robots.ts` allows all and references
the sitemap URL. Sitemap revalidates every 3600s for new slugs added
between deploys.

**Alternatives considered**:
- Static array of slugs — rejected, drifts.
- Skip sitemap until 4b — rejected, ~30 LOC for OSS site polish.
- Single `getFragrances({ limit: 1000 })` call — rejected, violates
  the OpenAPI `maximum: 100` constraint.

**Rationale**: Free SEO surface for a portfolio-grade OSS project.

> **Note on `lastModified`**: `FragranceListItem` does NOT carry an
> `updated_at` field today (verified against `apps/api/openapi.json`).
> We therefore stamp every fragrance entry with the sitemap's build
> time. When P1+ adds an `updated_at` column to the catalog tables,
> swap the value in. The fix is one line in `sitemap.ts`.

## Data Flow

```
User → Vercel Edge → Next.js 16 RSC route
                       │
                       ├─ awaits searchParams (filters)
                       │
                       ▼
                  fetchers.ts (typed openapi-fetch)
                       │
                       │ next: { revalidate, tags }
                       ▼
                  Vercel Data Cache  ──hit──→ HTML
                       │ miss
                       ▼
                  Fly.io API   GET /api/v1/...
                       │
                       │ Cache-Control: max-age=60, swr=300
                       ▼
                  Cloudflare CDN ──hit──→ JSON
                       │ miss
                       ▼
                  Postgres (catalog tables)
```

Filter clicks trigger a `<Link href="/fragrances?accord=woody">` push,
which causes Next.js to re-render the `/fragrances` server segment with
the new `searchParams`, hits the cache (or revalidates), and re-renders
the grid. Sidebar, header, footer stay mounted.

## File Changes

### New files

| File | Purpose |
|---|---|
| `apps/web/styles/tokens.css` | CSS custom properties (color, spacing, radii, shadows, font scale) under `:root` — light theme only |
| `apps/web/scripts/generate-api-types.mjs` | Runs `openapi-typescript apps/api/openapi.json -o apps/web/lib/api/types.ts` |
| `apps/web/lib/api/types.ts` | Generated; tracked in git; CI gate |
| `apps/web/lib/api/client.ts` | Typed `openapi-fetch` client |
| `apps/web/lib/api/fetchers.ts` | `getFragrances`, `getFragranceBySlug`, `getFeaturedFragrances` typed helpers |
| `apps/web/lib/glossary.tsx` | 12 seed glossary terms + `wrapGlossary` helper (`.tsx` because the helper returns React nodes) |
| `apps/web/components/ui/{sheet,tooltip,accordion,command,skeleton,popover,scroll-area,breadcrumb,select,pagination}.tsx` | New shadcn primitives (CLI generated) |
| `apps/web/components/site/Header.tsx` | Sticky header with disabled search |
| `apps/web/components/site/Footer.tsx` | GitHub / License / Contributing links |
| `apps/web/components/site/MobileMenu.tsx` | shadcn sheet drawer |
| `apps/web/components/site/Container.tsx` | Page-chrome wrapper |
| `apps/web/components/site/SkipToContent.tsx` | a11y skip link |
| `apps/web/components/site/Glossary.tsx` | Tooltip wrapper for jargon |
| `apps/web/components/catalog/FragranceCard.tsx` | Card component |
| `apps/web/components/catalog/FragranceCardSkeleton.tsx` | Skeleton variant |
| `apps/web/components/catalog/Pyramid.tsx` | Top/heart/base notes display |
| `apps/web/components/catalog/AccordBadge.tsx` | Accord chip |
| `apps/web/components/catalog/NoteBadge.tsx` | Note chip |
| `apps/web/components/catalog/ImageFallback.tsx` | Deterministic colored panel |
| `apps/web/components/catalog/Pagination.tsx` | URL-driven pagination (wraps shadcn pagination) |
| `apps/web/components/catalog/FilterSidebar.tsx` | Collapsible filter groups |
| `apps/web/app/(site)/layout.tsx` | Wraps children with Header + main + Footer |
| `apps/web/app/(site)/page.tsx` | Home |
| `apps/web/app/(site)/fragrances/page.tsx` | List with filters + pagination |
| `apps/web/app/(site)/fragrances/[slug]/page.tsx` | Detail |
| `apps/web/app/(site)/loading.tsx` | Route-segment skeleton |
| `apps/web/app/(site)/error.tsx` | Route-segment error boundary |
| `apps/web/app/(site)/not-found.tsx` | Custom 404 |
| `apps/web/app/sitemap.ts` | Build-time API → sitemap |
| `apps/web/app/robots.ts` | Allow-all + sitemap ref |
| `apps/web/__tests__/FragranceCard.test.tsx` | Render + a11y |
| `apps/web/__tests__/ImageFallback.test.tsx` | Color determinism |
| `apps/web/__tests__/Pyramid.test.tsx` | With/without roles |
| `apps/web/__tests__/Pagination.test.tsx` | Boundary disable |
| `apps/web/__tests__/Glossary.test.tsx` | Tooltip presence |
| `apps/web/e2e/fragrances.spec.ts` | Playwright list smoke |
| `apps/web/e2e/fragrance-detail.spec.ts` | Playwright detail smoke |

### Modified files

| File | Change |
|---|---|
| `apps/web/app/layout.tsx` | Drop Inter; load Fraunces+Manrope+JetBrains Mono via `next/font/google` with CSS variables; wrap with `<ThemeProvider forcedTheme="light">`; import `tokens.css` (via globals.css) |
| `apps/web/app/page.tsx` | Move home into `app/(site)/page.tsx` (delete this file) |
| `apps/web/app/globals.css` | `@import "./tokens.css"` after Tailwind import; add `@theme` mapping for font variables |
| `apps/web/components/theme-provider.tsx` | Add `forcedTheme="light"` default in caller; provider stays generic |
| `apps/web/next.config.ts` | Add `images.remotePatterns` for R2 host (`https://images.fragwise.app/**`) and localhost |
| `apps/web/package.json` | + `openapi-fetch` (deps); + `openapi-typescript` (devDeps); + scripts: `generate-api-types`, `predev`, `prebuild` |
| `apps/web/e2e/home.spec.ts` | Assert brand + featured strip |
| `package.json` (root) | + `generate-api-types` script that runs `pnpm --filter web generate-api-types` |
| `justfile` | Add `generate-types` recipe (mirror of `emit-openapi`) |
| `.github/workflows/web.yml` | Add `Re-emit OpenAPI & check upstream stale`, `Generate API types & check stale`, and `Bundle budget` steps |
| `apps/web/.size-limit.json` | size-limit config — 220 KB gzipped per surface |

## Interfaces / Contracts

### `apps/web/styles/tokens.css` (full content, paste-ready)

```css
/*
 * Fragwise design tokens — light theme only (4a).
 * Editorial-perfumery direction (ADR-0033).
 * Dark theme tokens are intentionally absent; deferred to 4b (ADR-0037).
 */

:root {
  /* Tell the UA we are committed to a light surface for native widgets
   * (scrollbars, autofill, disabled inputs, form controls). Without
   * this, OS dark-mode users see dark-themed native UI on top of our
   * ivory background. (4a is light-only — see ADR-0037.) */
  color-scheme: light;

  /* Color (oklch, perceptually uniform) */
  --color-background: oklch(0.985 0.005 90);
  --color-foreground: oklch(0.21 0.025 270);

  --color-card: oklch(0.99 0.003 90);
  --color-card-foreground: oklch(0.21 0.025 270);

  --color-popover: oklch(0.99 0.003 90);
  --color-popover-foreground: oklch(0.21 0.025 270);

  --color-muted: oklch(0.95 0.008 90);
  --color-muted-foreground: oklch(0.46 0.02 270);

  --color-primary: oklch(0.30 0.05 35);
  --color-primary-foreground: oklch(0.985 0.005 90);

  --color-secondary: oklch(0.94 0.012 70);
  --color-secondary-foreground: oklch(0.21 0.025 270);

  --color-accent: oklch(0.62 0.12 30);
  --color-accent-foreground: oklch(0.985 0.005 90);

  --color-destructive: oklch(0.55 0.20 27);
  --color-destructive-foreground: oklch(0.985 0.005 90);

  --color-border: oklch(0.90 0.008 90);
  --color-input: oklch(0.90 0.008 90);
  --color-ring: oklch(0.62 0.12 30);

  /* Spacing scale (4px base) */
  --space-0: 0;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;
  --space-16: 4rem;
  --space-20: 5rem;
  --space-24: 6rem;

  /* Radii */
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-full: 9999px;

  /* Shadows (deliberately soft) */
  --shadow-sm: 0 1px 2px oklch(0.21 0.025 270 / 0.04);
  --shadow-md: 0 4px 12px oklch(0.21 0.025 270 / 0.06);
  --shadow-lg: 0 12px 32px oklch(0.21 0.025 270 / 0.08);

  /* Type scale (Manrope body baseline) */
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 1.875rem;
  --font-size-4xl: 2.25rem;
  --font-size-5xl: 3rem;
  --font-size-6xl: 3.75rem;

  /* Line heights */
  --line-height-tight: 1.1;
  --line-height-snug: 1.3;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.65;
}
```

### `apps/web/app/globals.css` (full content, paste-ready)

```css
@import "tailwindcss";
@import "../styles/tokens.css";

/*
 * Tailwind v4 @theme: map our tokens into Tailwind's design system
 * so utility classes (bg-background, text-foreground, font-display)
 * resolve to our CSS variables.
 */
@theme inline {
  --color-background: var(--color-background);
  --color-foreground: var(--color-foreground);
  --color-card: var(--color-card);
  --color-card-foreground: var(--color-card-foreground);
  --color-popover: var(--color-popover);
  --color-popover-foreground: var(--color-popover-foreground);
  --color-muted: var(--color-muted);
  --color-muted-foreground: var(--color-muted-foreground);
  --color-primary: var(--color-primary);
  --color-primary-foreground: var(--color-primary-foreground);
  --color-secondary: var(--color-secondary);
  --color-secondary-foreground: var(--color-secondary-foreground);
  --color-accent: var(--color-accent);
  --color-accent-foreground: var(--color-accent-foreground);
  --color-destructive: var(--color-destructive);
  --color-destructive-foreground: var(--color-destructive-foreground);
  --color-border: var(--color-border);
  --color-input: var(--color-input);
  --color-ring: var(--color-ring);

  --radius: var(--radius-md);
  --radius-sm: var(--radius-sm);
  --radius-md: var(--radius-md);
  --radius-lg: var(--radius-lg);

  --font-display: var(--font-display);
  --font-sans: var(--font-sans);
  --font-mono: var(--font-mono);
}

/* Base typography */
html {
  font-family: var(--font-sans), system-ui, sans-serif;
  color: var(--color-foreground);
  background: var(--color-background);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

h1, h2, h3, .font-display {
  font-family: var(--font-display), serif;
  letter-spacing: -0.01em;
}

code, kbd, samp, .font-mono {
  font-family: var(--font-mono), ui-monospace, monospace;
}

/* a11y: visible focus ring on every focusable */
:where(a, button, input, select, textarea, [tabindex]):focus-visible {
  outline: 2px solid var(--color-ring);
  outline-offset: 2px;
}
```

### `apps/web/app/layout.tsx` (full content, paste-ready)

```tsx
import type { Metadata } from "next";
import { Fraunces, Manrope, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["400", "500", "600"],
});

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Fragwise",
  description: "Open-source fragrance discovery with an AI chatbot guide.",
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://fragwise.app"),
};

// R3 fix: only `viewport.colorScheme` should emit the meta tag. The
// previous design also set `metadata.other["color-scheme"]`, producing
// a duplicate `<meta name="color-scheme">`. Drop the metadata.other
// path; rely on viewport.colorScheme alone (Next.js 14+).
// Pair with `color-scheme: light` in tokens.css for the CSS-side
// declaration. ADR-0037: 4a is light-only.
export const viewport: import("next").Viewport = {
  colorScheme: "light",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${fraunces.variable} ${manrope.variable} ${jetbrainsMono.variable} antialiased`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          forcedTheme="light"
          enableSystem={false}
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

### `apps/web/components/theme-provider.tsx` (unchanged shape; light forced via props above)

Existing file is generic; props at the call site lock it to light.

### `apps/web/scripts/generate-api-types.mjs` (full content, paste-ready)

```js
#!/usr/bin/env node
// Generates apps/web/lib/api/types.ts from apps/api/openapi.json.
// Wired via predev/prebuild + CI stale check.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const here = new URL(".", import.meta.url).pathname;
const root = resolve(here, "..", "..", "..");
const input = resolve(root, "apps", "api", "openapi.json");
const output = resolve(root, "apps", "web", "lib", "api", "types.ts");

if (!existsSync(input)) {
  console.error(
    `[generate-api-types] missing ${input}\n` +
      `Run \`just emit-openapi\` first (or \`pnpm --filter api emit-openapi\`).`
  );
  process.exit(1);
}

const result = spawnSync(
  "pnpm",
  ["exec", "openapi-typescript", input, "-o", output],
  { stdio: "inherit", cwd: resolve(root, "apps", "web") }
);
process.exit(result.status ?? 1);
```

(Verified per Context7: `openapi-typescript <input> -o <output>` is the
current 7.x CLI shape.)

### `apps/web/lib/api/client.ts` (full content, paste-ready)

```ts
import createClient from "openapi-fetch";
import type { paths } from "./types";

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Typed openapi-fetch client. All catalog reads go through this.
 *
 * Per Context7 docs, the per-call init object passes through to the
 * underlying fetch — Next.js's `next: { revalidate, tags }` extensions
 * ride along unchanged when supplied via `fetchers.ts`.
 */
export const apiClient = createClient<paths>({ baseUrl });
```

### `apps/web/lib/api/fetchers.ts` (full content, paste-ready)

```ts
import { notFound } from "next/navigation";
import { apiClient } from "./client";
import type { components } from "./types";

export type FragranceListItem = components["schemas"]["FragranceListItem"];
export type FragranceDetail = components["schemas"]["FragranceDetail"];
export type Pagination = components["schemas"]["Pagination"];
export type Gender = components["schemas"]["Gender"];
export type AccordSummary = components["schemas"]["AccordSummary"];

export interface FragranceListParams {
  limit?: number;
  offset?: number;
  brand?: string;
  perfumer?: string[];
  gender?: Gender;
  year_min?: number;
  year_max?: number;
  concentration?: string;
  accord?: string[];
  note?: string[];
}

/**
 * Sort array-valued query params so `?accord=a&accord=b` and
 * `?accord=b&accord=a` produce the same Vercel cache key. Without
 * canonicalization, two equivalent filter selections fragment the
 * cache and double-fetch upstream. Apply the same canonicalization in
 * the URL the user sees (see `pickQuery` on the list page).
 */
function canonicalizeQuery<T extends Record<string, unknown>>(params: T): T {
  const out: Record<string, unknown> = { ...params };
  for (const key of Object.keys(out)) {
    const value = out[key];
    if (Array.isArray(value)) {
      out[key] = [...value].sort();
    }
  }
  return out as T;
}

/** GET /api/v1/fragrances — list with filters + pagination. */
export async function getFragrances(params: FragranceListParams = {}) {
  const query = canonicalizeQuery(params);
  const { data, error, response } = await apiClient.GET("/api/v1/fragrances", {
    params: { query },
    // Native fetch options pass through (verified Context7):
    next: {
      revalidate: 300,
      tags: ["fragrances:list"],
    },
  });
  if (error) {
    throw new Error(
      `getFragrances failed (${response.status}): ${JSON.stringify(error)}`
    );
  }
  if (!data) {
    throw new Error("getFragrances returned no data");
  }
  return data;
}

/**
 * GET /api/v1/accords — full taxonomy (no pagination per the spec
 * envelope). Used to populate FilterSidebar's accord facet so we
 * never render a hardcoded slug list that drifts from seed data.
 */
export async function getAllAccords(): Promise<AccordSummary[]> {
  const { data, error, response } = await apiClient.GET("/api/v1/accords", {
    next: { revalidate: 3600, tags: ["accords:all"] },
  });
  if (error) {
    throw new Error(
      `getAllAccords failed (${response.status}): ${JSON.stringify(error)}`
    );
  }
  return data?.data ?? [];
}

// NOTE: there is no `/api/v1/concentrations` endpoint in the current
// `apps/api/openapi.json`. The concentration filter therefore falls
// back to a small static list (EDT/EDP/Parfum) sourced from
// `lib/glossary` term keys until a follow-up phase adds the endpoint.
// Tracked in Open Questions as a P1 follow-up.

/** GET /api/v1/fragrances/{slug} — detail; calls notFound() on 404. */
export async function getFragranceBySlug(slug: string) {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/fragrances/{slug}",
    {
      params: { path: { slug } },
      next: {
        revalidate: 600,
        tags: [`fragrance:${slug}`],
      },
    }
  );
  if (response.status === 404) notFound();
  if (error) {
    throw new Error(
      `getFragranceBySlug(${slug}) failed (${response.status}): ${JSON.stringify(error)}`
    );
  }
  if (!data) notFound();
  return data;
}

/**
 * Featured fragrances strip (home).
 * No `featured=` flag exists in P1 — we read the first N via the list
 * endpoint sorted by default order. When P5 adds curation, swap the
 * underlying call here without touching home/page.tsx.
 */
export async function getFeaturedFragrances(limit = 6) {
  const { data, error, response } = await apiClient.GET("/api/v1/fragrances", {
    params: { query: { limit } },
    next: { revalidate: 600, tags: ["featured"] },
  });
  if (error) {
    throw new Error(
      `getFeaturedFragrances failed (${response.status}): ${JSON.stringify(error)}`
    );
  }
  return data?.data ?? [];
}
```

> **Note on contract**: P1 `FragranceListItem` and `FragranceDetail` do
> NOT carry an `image_url` field today (verified against
> `apps/api/openapi.json`). Therefore EVERY catalog surface in 4a uses
> `ImageFallback` exclusively. When P1+ adds `image_url`, the image
> components fall back conditionally — see `FragranceCard` skeleton
> below.

### `apps/web/package.json` (delta)

```jsonc
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "size": "size-limit",
    "generate-api-types": "node scripts/generate-api-types.mjs",
    "predev": "node scripts/generate-api-types.mjs",
    "prebuild": "node scripts/generate-api-types.mjs"
  },
  "dependencies": {
    "openapi-fetch": "^0.13.0"
    // ... existing deps
  },
  "devDependencies": {
    "openapi-typescript": "^7.6.0",
    "size-limit": "^11.0.0",
    "@size-limit/preset-app": "^11.0.0"
    // ... existing devDeps
  }
}
```

### Root `package.json` (add script)

```jsonc
{
  "scripts": {
    // ... existing
    "generate-api-types": "pnpm --filter web generate-api-types"
  }
}
```

### `justfile` recipe (paste at end)

```makefile
# Regenerate apps/web/lib/api/types.ts from apps/api/openapi.json.
generate-types:
    pnpm --filter web generate-api-types
```

### `.github/workflows/web.yml` (add steps before "Lint" and after "Build")

The web workflow grows TWO new gates: an upstream OpenAPI freshness
re-check (so a stale `apps/api/openapi.json` cannot silently keep
`types.ts` "fresh"), and a `size-limit` budget gate.

```yaml
      - name: Re-emit OpenAPI and check upstream stale
        # Without this, a stale apps/api/openapi.json + a stale
        # apps/web/lib/api/types.ts both pass `git diff --exit-code`
        # and CI goes green while runtime types drift. We require the
        # FastAPI source-of-truth to be fresh too.
        run: |
          uv run --project apps/api python apps/api/scripts/emit_openapi.py
          if ! git diff --exit-code apps/api/openapi.json; then
            echo "::error::apps/api/openapi.json is stale. Run 'just emit-openapi' and commit."
            exit 1
          fi

      - name: Generate API types and check stale
        run: |
          pnpm --filter web generate-api-types
          if ! git diff --exit-code apps/web/lib/api/types.ts; then
            echo "::error::apps/web/lib/api/types.ts is stale. Run 'just generate-types' and commit."
            exit 1
          fi

      # ... lint, typecheck, build run here ...

      - name: Bundle budget
        run: pnpm --filter web exec size-limit
```

### `apps/web/next.config.ts` (full content, paste-ready)

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.fragwise.app",
        pathname: "/**",
      },
      // Local dev fallback for placeholder paths under /public:
      {
        protocol: "http",
        hostname: "localhost",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
```

> **Open question (R2 hostname)**: confirm `images.fragwise.app` is the
> public R2 CDN hostname per Phase 0c. If it differs, the design's only
> mechanical edit is this string. Tracked in Open Questions.

### shadcn primitives — install command

```bash
cd apps/web && npx shadcn@latest add sheet tooltip accordion command \
  skeleton popover scroll-area breadcrumb select pagination
```

(Verified Context7: each primitive supports `npx shadcn@latest add
<name>`; the CLI accepts multiple names per call.)

### `apps/web/components/site/Header.tsx` (paste-ready)

> R3 fix: Header is a **Server Component** again. Promoting it to
> `"use client"` purely to host a lazy import shipped the entire NAV
> + Search input + lucide icons as client JS, partially undoing W6's
> bundle goal. Instead, `MobileMenu` is its own Client Component
> (`"use client"` at top of `MobileMenu.tsx`) — Radix's Sheet primitive
> already lazy-renders its portal contents on `open`. No `next/dynamic`
> wrapper is needed.

```tsx
import Link from "next/link";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { MobileMenu } from "./MobileMenu";

const NAV: { href: string; label: string; placeholder?: boolean }[] = [
  { href: "/", label: "Home" },
  { href: "/fragrances", label: "Fragrances" },
  // 4b targets — render as links; routes 404 until 4b lands.
  { href: "/notes", label: "Notes", placeholder: true },
  { href: "/accords", label: "Accords", placeholder: true },
  { href: "/brands", label: "Brands", placeholder: true },
  { href: "/perfumers", label: "Perfumers", placeholder: true },
  { href: "/articles", label: "Journal", placeholder: true },
];

export function Header() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-4 sm:px-6">
        <Link href="/" className="font-display text-2xl font-medium tracking-tight">
          Fragwise
        </Link>
        <nav className="hidden items-center gap-6 md:flex">
          {NAV.map((item) =>
            item.placeholder ? (
              // 4b targets — render as non-interactive labels until
              // those routes ship. Avoids 404s on click while signalling
              // the surface is planned.
              <span
                key={item.href}
                aria-disabled="true"
                title="Coming with phase 4b"
                className="text-sm text-muted-foreground/50 cursor-not-allowed"
              >
                {item.label}
              </span>
            ) : (
              <Link
                key={item.href}
                href={item.href}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {item.label}
              </Link>
            )
          )}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          <label className="relative">
            <Search
              aria-hidden
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              type="search"
              placeholder="Search coming soon"
              disabled
              aria-label="Search (coming soon)"
              className="w-64 pl-9 font-mono text-xs"
            />
          </label>
        </div>
        <MobileMenu nav={NAV} />
      </div>
    </header>
  );
}
```

### `apps/web/components/site/MobileMenu.tsx` (paste-ready)

```tsx
"use client";
import Link from "next/link";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

export function MobileMenu({
  nav,
}: {
  nav: { href: string; label: string; placeholder?: boolean }[];
}) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
          <Menu />
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-72">
        <SheetHeader>
          <SheetTitle className="font-display">Fragwise</SheetTitle>
        </SheetHeader>
        <nav className="mt-6 flex flex-col gap-3">
          {nav.map((item) =>
            item.placeholder ? (
              <span
                key={item.href}
                aria-disabled="true"
                className="text-base text-muted-foreground/50 cursor-not-allowed"
              >
                {item.label}
                <span className="ml-2 font-mono text-[0.6rem] uppercase tracking-wider">
                  4b
                </span>
              </span>
            ) : (
              <Link
                key={item.href}
                href={item.href}
                className="text-base text-foreground transition-colors hover:text-accent"
              >
                {item.label}
              </Link>
            )
          )}
        </nav>
      </SheetContent>
    </Sheet>
  );
}
```

### `apps/web/components/site/Footer.tsx` (paste-ready)

```tsx
const REPO = "https://github.com/Iam2Fast/fragwise";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border bg-secondary/40">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-12 sm:px-6 md:flex-row md:items-center md:justify-between">
        <p className="font-display text-xl">Fragwise</p>
        <nav className="flex flex-wrap gap-6 font-mono text-xs uppercase tracking-wider text-muted-foreground">
          <a href={REPO} target="_blank" rel="noreferrer noopener">GitHub</a>
          <a href={`${REPO}/blob/main/LICENSE`} target="_blank" rel="noreferrer noopener">License</a>
          <a href={`${REPO}/blob/main/CONTRIBUTING.md`} target="_blank" rel="noreferrer noopener">Contributing</a>
        </nav>
        <p className="text-xs text-muted-foreground">© {new Date().getFullYear()} Fragwise — Apache-2.0</p>
      </div>
    </footer>
  );
}
```

### `apps/web/components/site/SkipToContent.tsx` (paste-ready)

```tsx
export function SkipToContent() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
    >
      Skip to content
    </a>
  );
}
```

### `apps/web/components/site/Container.tsx` (paste-ready)

```tsx
import { cn } from "@/lib/utils";

export function Container({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mx-auto max-w-7xl px-4 sm:px-6", className)}>
      {children}
    </div>
  );
}
```

### `apps/web/components/site/Glossary.tsx` (paste-ready)

> **Why Popover instead of Tooltip**: Radix `Tooltip` is hover/focus
> only and does not fire on touch — mobile users tapping the dotted
> underline get nothing back. Popover is click/tap (and keyboard
> Enter/Space) driven, satisfying focus + touch from the spec. Hover
> users now tap once instead of relying on a hover delay; this is an
> acceptable trade-off given the alternative is a no-op on mobile.
> See ADR-0039 (revised). The `popover` shadcn primitive is already
> in the 10 added in 4a (ADR-0038).

```tsx
"use client";

import { glossary, type GlossaryKey } from "@/lib/glossary";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export function Glossary({
  termKey,
  children,
}: {
  termKey: GlossaryKey;
  children: React.ReactNode;
}) {
  const entry = glossary[termKey];
  if (!entry) return <>{children}</>;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`Glossary: ${entry.term}`}
          className="cursor-help inline-flex items-baseline border-b border-dotted border-accent text-current focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {children}
        </button>
      </PopoverTrigger>
      <PopoverContent side="top" className="max-w-xs text-sm leading-snug">
        <strong className="font-display font-semibold block mb-1">
          {entry.term}
        </strong>
        <span className="text-foreground/85">{entry.definition}</span>
      </PopoverContent>
    </Popover>
  );
}
```

### `apps/web/lib/glossary.ts` (paste-ready)

> The `wrapGlossary` helper at the bottom is the canonical way to
> render long-form catalog copy with first-mention term wrapping. The
> detail page MUST use it instead of ad-hoc `string.split(term)`
> patterns: a single-term split silently drops content past the second
> occurrence and only handles ONE term out of the 12 in this module
> (see C2 in the judgment-day pass).

```ts
import type { ComponentType, ReactNode } from "react";

export const glossary = {
  sillage: {
    term: "Sillage",
    definition:
      "The trail of scent a wearer leaves in the air. From French for ‘wake’.",
  },
  accord: {
    term: "Accord",
    definition:
      "A blend of notes that produces a single recognisable smell — a perfume’s building block.",
  },
  drydown: {
    term: "Drydown",
    definition:
      "The final phase of a fragrance, hours after application, when the base notes settle.",
  },
  chypre: {
    term: "Chypre",
    definition:
      "A family built on bergamot, oakmoss and labdanum. Refined, slightly bitter.",
  },
  fougere: {
    term: "Fougère",
    definition:
      "‘Fern-like’ — a classic accord of lavender, oakmoss and coumarin. The backbone of barbershop scents.",
  },
  oriental: {
    term: "Oriental (Amber)",
    definition:
      "Warm, resinous family — vanilla, amber, spices. Many houses now prefer ‘amber’.",
  },
  gourmand: {
    term: "Gourmand",
    definition:
      "Edible-smelling fragrances — vanilla, caramel, cocoa, coffee.",
  },
  aquatic: {
    term: "Aquatic",
    definition:
      "Fresh, marine, ozonic notes — calone, sea salt, melon-water accords.",
  },
  edt: {
    term: "EDT (Eau de Toilette)",
    definition:
      "Lighter concentration, typically 5–15% aromatic compounds. Lasts 3–5 hours.",
  },
  edp: {
    term: "EDP (Eau de Parfum)",
    definition:
      "Stronger concentration, 15–20%. Longer wear, richer drydown.",
  },
  parfum: {
    term: "Parfum (Extrait)",
    definition:
      "Highest concentration, 20–40%. Worn close to the skin; lasts all day.",
  },
  "top-heart-base": {
    term: "Top, heart, base",
    definition:
      "The pyramid: top notes greet you, heart notes appear after 20–30 min, base notes anchor for hours.",
  },
} as const;

export type GlossaryKey = keyof typeof glossary;

// Optional aliases per term (case-insensitive). The bare key is added
// implicitly by wrapGlossary, so e.g. `parfum` matches "parfum" without
// listing it here. Aliases extend that set with synonyms and inflections.
// R3 fix: `term` field can be a display form like "Parfum (Extrait)";
// we no longer use `term` as an alias source — only the lowercased key
// + this ALIASES map.
const ALIASES: Partial<Record<GlossaryKey, string[]>> = {
  sillage: ["sillages"],
  fougere: ["fougère", "fougeres", "fougères"],
  edt: ["eau de toilette"],
  edp: ["eau de parfum"],
  parfum: ["extrait", "extrait de parfum"],
  oriental: ["amber"],
  cologne: ["edc", "eau de cologne"],
  "top-heart-base": ["pyramid", "top notes", "heart notes", "base notes"],
};

/**
 * Wraps the FIRST occurrence (case-insensitive, word-boundary) of EACH
 * glossary term in the input with the supplied `<Glossary>` component.
 * All other text is preserved verbatim.
 *
 * Replaces the broken pattern `description.split(term)[0|1]` which:
 *  - silently drops text past the 2nd occurrence
 *  - is case-sensitive
 *  - handles only ONE term out of the 12
 *
 * The alternation pattern is built longest-first so shorter aliases
 * never swallow prefixes of longer ones.
 */
export function wrapGlossary(
  text: string,
  Glossary: ComponentType<{ termKey: GlossaryKey; children: ReactNode }>
): ReactNode {
  // R3 fix: alias set = lowercased KEY (always) + ALIASES synonyms.
  // We deliberately do NOT use glossary[key].term because it can be a
  // bracketed display form like "Parfum (Extrait)" that never appears
  // in user-authored prose. The bare key ("parfum") is what readers
  // actually write.
  const aliases: { key: GlossaryKey; alias: string }[] = (
    Object.keys(glossary) as GlossaryKey[]
  ).flatMap((key) => [
    { key, alias: key.replace(/-/g, " ") }, // bare key form, hyphens to spaces
    ...((ALIASES[key] ?? []).map((alias) => ({ key, alias }))),
  ]);
  aliases.sort((a, b) => b.alias.length - a.alias.length);

  // Build a Map for O(1) alias→key lookup at match time.
  const aliasIndex = new Map<string, GlossaryKey>();
  for (const { key, alias } of aliases) {
    const lower = alias.toLowerCase();
    if (!aliasIndex.has(lower)) aliasIndex.set(lower, key);
  }

  const escape = (s: string) =>
    s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // R3 fix: use Unicode-aware lookarounds (`u` flag + property escapes)
  // because `\b` is ASCII-only and fails on accented aliases like
  // "fougère". The lookarounds match a transition between letter/digit
  // and non-letter/digit on both sides, including non-ASCII letters.
  const pattern = new RegExp(
    `(?<![\\p{L}\\p{N}_])(${aliases.map((a) => escape(a.alias)).join("|")})(?![\\p{L}\\p{N}_])`,
    "giu"
  );

  const seen = new Set<GlossaryKey>();
  const out: ReactNode[] = [];
  let lastIndex = 0;
  for (const match of text.matchAll(pattern)) {
    const matched = match[0];
    const found = aliasIndex.get(matched.toLowerCase());
    if (!found) continue;
    if (seen.has(found)) continue; // first-mention only per term
    seen.add(found);
    const idx = match.index ?? 0;
    out.push(text.slice(lastIndex, idx));
    out.push(
      <Glossary key={`g-${idx}`} termKey={found}>
        {matched}
      </Glossary>
    );
    lastIndex = idx + matched.length;
  }
  out.push(text.slice(lastIndex));
  return out;
}
```

> Note: `wrapGlossary` returns React nodes, so `lib/glossary.ts` must
> be `.tsx` (rename) or the helper can live alongside in
> `lib/glossary.tsx`. The component import (`apps/web/components/site/Glossary`)
> is passed in to keep this module free of UI dependencies and
> hot-loop friendly in unit tests.

### `apps/web/components/catalog/FragranceCard.tsx` (paste-ready)

> The original draft imported `./GenderIcon` and a `lib/format.ts`
> helper that were never paste-ready in the inventory. Both are
> inlined below to keep the design self-contained — no missing-file
> drift between design and apply.

```tsx
import Link from "next/link";
import Image from "next/image";
import { Mars, Venus, CircleDot } from "lucide-react";
import { ImageFallback } from "./ImageFallback";
import type { FragranceListItem } from "@/lib/api/fetchers";

function genderIcon(gender: string) {
  switch (gender) {
    case "masc":
      return <Mars className="h-3.5 w-3.5" aria-label="masculine" />;
    case "fem":
      return <Venus className="h-3.5 w-3.5" aria-label="feminine" />;
    default:
      // covers "unisex" and "genderfree" — see Gender enum in
      // openapi.json: ["masc", "fem", "unisex", "genderfree"].
      return <CircleDot className="h-3.5 w-3.5" aria-label="unisex / genderfree" />;
  }
}

export function FragranceCard({ fragrance }: { fragrance: FragranceListItem }) {
  // P1 contract has no image_url field today (see fetchers.ts note).
  // ImageFallback is rendered unconditionally; conditional swap kept
  // ready for the day P1+ adds image_url.
  const imageUrl: string | null = null;

  return (
    <Link
      href={`/fragrances/${fragrance.slug}`}
      className="group flex flex-col gap-3 rounded-md outline-none transition-transform focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="relative aspect-[3/4] overflow-hidden rounded-md bg-card shadow-sm transition-shadow group-hover:shadow-md group-hover:-translate-y-0.5">
        {imageUrl ? (
          <Image
            src={imageUrl}
            alt={`${fragrance.name} bottle`}
            fill
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 33vw, 25vw"
            className="object-cover"
          />
        ) : (
          <ImageFallback slug={fragrance.slug} name={fragrance.name} />
        )}
      </div>
      <div className="flex flex-col gap-1.5">
        <span className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground">
          {fragrance.brand.name}
        </span>
        <span className="font-display text-lg leading-snug text-foreground">
          {fragrance.name}
        </span>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {fragrance.year_released ? (
            <span className="font-mono">{fragrance.year_released}</span>
          ) : null}
          {genderIcon(fragrance.gender)}
          {fragrance.concentration ? (
            <span className="font-mono uppercase">
              {fragrance.concentration.name}
            </span>
          ) : null}
        </div>
        {/* AccordBadges live inside the detail card slot; list cards stay sparse */}
      </div>
    </Link>
  );
}
```

### `apps/web/components/catalog/FragranceCardSkeleton.tsx` (paste-ready)

```tsx
import { Skeleton } from "@/components/ui/skeleton";

export function FragranceCardSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <Skeleton className="aspect-[3/4] rounded-md" />
      <Skeleton className="h-3 w-16" />
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-3 w-1/3" />
    </div>
  );
}
```

### `apps/web/components/catalog/ImageFallback.tsx` (paste-ready)

> **Contrast contract**: at HSL `(hue, 38%, 72%)`, perceived lightness
> drifts wildly across hues — yellow-greens (~70 hue) read MUCH lighter
> than dusk-blue (~200 hue). Pairing ivory text against the lighter
> bands fails WCAG AA. We switch the panel to `oklch(L=0.78 ...)` so
> perceived lightness is constant across the 6 hue bands, and use
> dark ink on every panel (passes AA at L=0.78 against the deep-ink
> foreground for the four light bands; the two cool bands at the same
> L still pass with the dark ink). See ADR-0036 (revised).
>
> Note on `node:crypto`: this module runs in the Node runtime (RSC,
> server tier). If any `(site)` route is later migrated to the Edge
> runtime, swap `createHash` for an async `crypto.subtle.digest("SHA-256", ...)`
> wrapper. We do NOT pin Edge runtime today, so the sync hash is fine.

```tsx
import { createHash } from "node:crypto";

const BANDS = [25, 35, 45, 70, 200, 280];

function panelOklch(slug: string): { bg: string; fg: string } {
  // Hash → hue band + small jitter; constant L=0.78 keeps perceived
  // lightness stable across hues so dark ink contrast is uniform.
  const h = createHash("sha256").update(slug).digest("hex");
  const band = parseInt(h.slice(0, 2), 16) % 6;
  const jitterByte = parseInt(h.slice(2, 4), 16);
  const jitter = (jitterByte % 12) - 6; // -6..+5
  const hue = BANDS[band] + jitter;
  return {
    bg: `oklch(0.78 0.06 ${hue})`,
    // Dark ink universally — at L=0.78 with chroma 0.06, every band
    // reads as a soft pastel; the deep-ink foreground passes AA on
    // all six. Foreground variable resolves to oklch(0.21 0.025 270).
    fg: "var(--color-foreground)",
  };
}

export function ImageFallback({
  slug,
  name,
}: {
  slug: string;
  name: string;
}) {
  const { bg, fg } = panelOklch(slug);
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  return (
    <div
      role="img"
      aria-label={`${name} (no bottle image available)`}
      className="absolute inset-0 flex items-end justify-start"
      style={{ backgroundColor: bg }}
    >
      <span
        className="font-display select-none"
        style={{
          color: fg,
          fontSize: "60%",
          lineHeight: 1,
          padding: "0 0 0.5em 0.4em",
          fontWeight: 600,
        }}
      >
        {initial}
      </span>
    </div>
  );
}
```

> Determinism contract: `panelOklch(slug)` is a pure function of `slug`.
> `__tests__/ImageFallback.test.tsx` asserts that two renders with the
> same slug produce identical inline `style` strings.

### `apps/web/components/catalog/Pyramid.tsx` (paste-ready)

```tsx
import { NoteBadge } from "./NoteBadge";
import type { components } from "@/lib/api/types";

type Notes = components["schemas"]["NotesByRole"];

const ROLES: { key: keyof Notes; label: string }[] = [
  { key: "top", label: "TOP" },
  { key: "heart", label: "HEART" },
  { key: "base", label: "BASE" },
];

export function Pyramid({ notes }: { notes: Notes }) {
  return (
    <div className="flex flex-col gap-6 border-l border-accent pl-6">
      {ROLES.map(({ key, label }) => {
        const list = notes[key] ?? [];
        return (
          <div key={key} className="flex flex-col gap-2">
            <span className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
              {label}
            </span>
            {list.length === 0 ? (
              <span aria-label={`No ${label.toLowerCase()} notes`} className="text-muted-foreground">
                —
              </span>
            ) : (
              <div className="flex flex-wrap gap-2">
                {list.map((n) => (
                  <NoteBadge key={n.slug} note={n} />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

### `apps/web/components/catalog/AccordBadge.tsx` and `NoteBadge.tsx` (paste-ready)

```tsx
// AccordBadge.tsx
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/api/types";

export function AccordBadge({
  accord,
}: {
  accord: components["schemas"]["AccordSummary"];
}) {
  return (
    <Link href={`/fragrances?accord=${accord.slug}`}>
      <Badge
        variant="secondary"
        className="font-mono text-[0.65rem] uppercase tracking-[0.16em]"
      >
        {accord.name}
      </Badge>
    </Link>
  );
}
```

```tsx
// NoteBadge.tsx — non-clickable in 4a (note details ship in 4b).
import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/api/types";

export function NoteBadge({
  note,
}: {
  note: components["schemas"]["NoteSummary"];
}) {
  return (
    <Badge variant="outline" className="font-sans text-sm">
      {note.name}
    </Badge>
  );
}
```

### `apps/web/components/catalog/Pagination.tsx` (paste-ready)

> Disabled boundary controls render as a `<span aria-disabled>` rather
> than a `<PaginationLink href="#">`. Two reasons: (1) keyboard
> Tab+Enter on a `<a href="#">` still navigates to `#` and jumps to
> top — `aria-disabled` is advisory and does NOT block activation;
> (2) `<span>` cannot be tabbed and cannot fire navigation. Adjacent
> page items + ellipses render inside `<React.Fragment>` rather than
> a `<span>` so the resulting DOM is `<ul><li>...</li><li>...</li></ul>`
> (valid) instead of `<ul><span><li>...</li></span></ul>` (invalid).

```tsx
import * as React from "react";
import {
  Pagination as Shell,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
  PaginationEllipsis,
} from "@/components/ui/pagination";

export function Pagination({
  total,
  limit,
  offset,
  hrefBase,
  searchParams,
}: {
  total: number;
  limit: number;
  offset: number;
  hrefBase: string;
  searchParams: URLSearchParams;
}) {
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.floor(offset / limit) + 1;
  const prevDisabled = offset === 0;
  const nextDisabled = offset + limit >= total;

  function urlFor(page: number) {
    const sp = new URLSearchParams(searchParams);
    sp.set("offset", String((page - 1) * limit));
    sp.set("limit", String(limit));
    return `${hrefBase}?${sp.toString()}`;
  }

  // Window pages: first, current-1, current, current+1, last (ellipsis between).
  const pages = new Set<number>([1, totalPages, currentPage - 1, currentPage, currentPage + 1]);
  const sortedPages = [...pages].filter((p) => p >= 1 && p <= totalPages).sort((a, b) => a - b);

  return (
    <Shell>
      <PaginationContent>
        {prevDisabled ? (
          <PaginationItem>
            <span
              aria-disabled="true"
              aria-label="No previous page"
              className="select-none opacity-40 px-3 py-2 inline-flex items-center"
            >
              ‹ Prev
            </span>
          </PaginationItem>
        ) : (
          <PaginationItem>
            <PaginationPrevious href={urlFor(currentPage - 1)} />
          </PaginationItem>
        )}

        {sortedPages.map((p, i) => {
          const prev = sortedPages[i - 1];
          const needsEllipsis = prev !== undefined && p - prev > 1;
          return (
            <React.Fragment key={p}>
              {needsEllipsis ? (
                <PaginationItem>
                  <PaginationEllipsis />
                </PaginationItem>
              ) : null}
              <PaginationItem>
                <PaginationLink href={urlFor(p)} isActive={p === currentPage}>
                  {p}
                </PaginationLink>
              </PaginationItem>
            </React.Fragment>
          );
        })}

        {nextDisabled ? (
          <PaginationItem>
            <span
              aria-disabled="true"
              aria-label="No next page"
              className="select-none opacity-40 px-3 py-2 inline-flex items-center"
            >
              Next ›
            </span>
          </PaginationItem>
        ) : (
          <PaginationItem>
            <PaginationNext href={urlFor(currentPage + 1)} />
          </PaginationItem>
        )}
      </PaginationContent>
    </Shell>
  );
}
```

### `apps/web/components/catalog/FilterSidebar.tsx` (paste-ready)

> **`"use client"` is REQUIRED** because this component renders Radix
> `Accordion`, which mounts state-bearing client primitives. Server
> Component → Client Component prop boundaries also mean we cannot
> pass a non-serializable `URLSearchParams` instance — props must be
> plain JSON. The signature accepts `Record<string, string | string[]>`
> (the same shape Next.js gives us from `searchParams`) and lazily
> reconstructs a URLSearchParams inside the component for href building.

```tsx
"use client";

import Link from "next/link";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";

const GENDERS = [
  { slug: "masc", label: "Masculine" },
  { slug: "fem", label: "Feminine" },
  { slug: "unisex", label: "Unisex" },
  { slug: "genderfree", label: "Genderfree" },
];

export interface FilterSidebarProps {
  pathname: string;
  /**
   * Plain serializable shape so this Client Component receives a
   * cross-boundary-safe prop. Convert in the parent via
   * `Object.fromEntries(...)` over the awaited `searchParams`.
   */
  searchParams: Record<string, string | string[]>;
  facets: {
    accords: { slug: string; name: string }[];
    brands: { slug: string; name: string }[];
    concentrations: { slug: string; name: string }[];
  };
}

function toUSP(sp: Record<string, string | string[]>): URLSearchParams {
  const out = new URLSearchParams();
  for (const k of Object.keys(sp).sort()) {
    const v = sp[k];
    if (v == null || v === "") continue;
    const list = Array.isArray(v) ? [...v].sort() : [v];
    list.forEach((vv) => out.append(k, vv));
  }
  return out;
}

function withParam(sp: URLSearchParams, key: string, value: string, mode: "set" | "add" | "remove") {
  const next = new URLSearchParams(sp);
  if (mode === "set") next.set(key, value);
  if (mode === "add") {
    // R3 fix: dedupe via Set so re-clicking an already-active filter
    // doesn't produce `?accord=woody&accord=woody`. Then sort to keep
    // the URL canonical (cache-key stable).
    const merged = [...new Set([...next.getAll(key), value])].sort();
    next.delete(key);
    merged.forEach((v) => next.append(key, v));
  }
  if (mode === "remove") {
    const list = next.getAll(key).filter((v) => v !== value).sort();
    next.delete(key);
    list.forEach((v) => next.append(key, v));
  }
  next.delete("offset"); // any filter change resets pagination
  return next.toString();
}

export function FilterSidebar({ pathname, searchParams, facets }: FilterSidebarProps) {
  const usp = toUSP(searchParams);
  const activeAccords = usp.getAll("accord");
  const activeGender = usp.get("gender");
  const activeBrand = usp.get("brand");

  const hasActive = [...usp.keys()].some((k) =>
    ["accord", "gender", "brand", "year_min", "year_max", "concentration", "note"].includes(k)
  );

  return (
    <aside className="flex flex-col gap-6 text-sm" aria-label="Filters">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl">Refine</h2>
        {hasActive ? (
          <Link
            href={pathname}
            className="font-mono text-xs uppercase tracking-wider text-accent hover:underline"
          >
            Clear all
          </Link>
        ) : null}
      </div>

      {activeAccords.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {activeAccords.map((slug) => (
            <Link
              key={slug}
              href={`${pathname}?${withParam(usp, "accord", slug, "remove")}`}
              aria-label={`Remove ${slug} filter`}
            >
              <Badge variant="default" className="gap-1">
                {slug} ×
              </Badge>
            </Link>
          ))}
        </div>
      ) : null}

      <Accordion type="multiple" defaultValue={["gender", "accord", "brand"]}>
        <AccordionItem value="gender">
          <AccordionTrigger>Gender</AccordionTrigger>
          <AccordionContent>
            <ul className="flex flex-col gap-2">
              {GENDERS.map((g) => {
                const isActive = activeGender === g.slug;
                const href = isActive
                  ? `${pathname}?${withParam(usp, "gender", g.slug, "remove")}`
                  : `${pathname}?${withParam(usp, "gender", g.slug, "set")}`;
                return (
                  <li key={g.slug}>
                    {/* `aria-current` is the correct attribute for an
                        anchor representing the currently-applied filter.
                        `aria-pressed` is for buttons, not links, and is
                        invalid on an <a>. */}
                    <Link
                      href={href}
                      aria-current={isActive ? "true" : undefined}
                      className={isActive ? "text-accent" : "text-foreground"}
                    >
                      {g.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="accord">
          <AccordionTrigger>Accord</AccordionTrigger>
          <AccordionContent>
            <ul className="flex flex-col gap-2 max-h-72 overflow-y-auto">
              {facets.accords.map((a) => {
                const isActive = activeAccords.includes(a.slug);
                const href = isActive
                  ? `${pathname}?${withParam(usp, "accord", a.slug, "remove")}`
                  : `${pathname}?${withParam(usp, "accord", a.slug, "add")}`;
                return (
                  <li key={a.slug}>
                    <Link
                      href={href}
                      aria-current={isActive ? "true" : undefined}
                      className={isActive ? "text-accent" : "text-foreground"}
                    >
                      {a.name}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="brand">
          <AccordionTrigger>Brand</AccordionTrigger>
          <AccordionContent>
            <ul className="flex flex-col gap-2 max-h-72 overflow-y-auto">
              {facets.brands.map((b) => {
                const isActive = activeBrand === b.slug;
                const href = isActive
                  ? `${pathname}?${withParam(usp, "brand", b.slug, "remove")}`
                  : `${pathname}?${withParam(usp, "brand", b.slug, "set")}`;
                return (
                  <li key={b.slug}>
                    <Link
                      href={href}
                      aria-current={isActive ? "true" : undefined}
                      className={isActive ? "text-accent" : "text-foreground"}
                    >
                      {b.name}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="concentration">
          <AccordionTrigger>Concentration</AccordionTrigger>
          <AccordionContent>
            <ul className="flex flex-col gap-2">
              {facets.concentrations.map((c) => {
                const isActive = usp.get("concentration") === c.slug;
                const href = isActive
                  ? `${pathname}?${withParam(usp, "concentration", c.slug, "remove")}`
                  : `${pathname}?${withParam(usp, "concentration", c.slug, "set")}`;
                return (
                  <li key={c.slug}>
                    <Link
                      href={href}
                      aria-current={isActive ? "true" : undefined}
                      className={isActive ? "text-accent" : "text-foreground"}
                    >
                      {c.name}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="year">
          <AccordionTrigger>Year</AccordionTrigger>
          <AccordionContent>
            <p className="text-xs text-muted-foreground">
              Year range filter via URL params <code className="font-mono">year_min</code> / <code className="font-mono">year_max</code>.
              Slider control deferred to 4b; the API params are wired today.
            </p>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </aside>
  );
}
```

### `apps/web/app/(site)/layout.tsx` (paste-ready)

```tsx
import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { SkipToContent } from "@/components/site/SkipToContent";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SkipToContent />
      <Header />
      <main id="main-content" className="min-h-[calc(100dvh-4rem)]">
        {children}
      </main>
      <Footer />
    </>
  );
}
```

### `apps/web/app/(site)/page.tsx` — Home (paste-ready)

```tsx
import Link from "next/link";
import { Container } from "@/components/site/Container";
import { FragranceCard } from "@/components/catalog/FragranceCard";
import { getFeaturedFragrances } from "@/lib/api/fetchers";

const MOODS = [
  { slug: "fresh", label: "Fresh & bright" },
  { slug: "woody", label: "Woody & smoky" },
  { slug: "floral", label: "Floral & soft" },
  { slug: "gourmand", label: "Sweet & comforting" },
  { slug: "oriental", label: "Warm & spiced" },
  { slug: "aquatic", label: "Aquatic & cool" },
];

export default async function HomePage() {
  const featured = await getFeaturedFragrances(6);

  return (
    <>
      {/* Hero — asymmetric editorial */}
      <section className="border-b border-border bg-secondary/40">
        <Container className="grid gap-10 py-20 md:grid-cols-12 md:py-32">
          <div className="md:col-span-7 md:col-start-2">
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
              An open catalogue of perfume
            </p>
            <h1 className="mt-4 font-display text-5xl font-medium leading-[1.05] tracking-tight md:text-7xl">
              Fragrance, <em className="italic text-accent">read closely</em>.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-muted-foreground">
              A reference for the curious — connoisseur and beginner alike. Browse by note, accord, or mood, and let the journal explain the rest.
            </p>
            <div className="mt-8 flex gap-4">
              <Link
                href="/fragrances"
                className="rounded-md bg-primary px-5 py-2.5 font-mono text-xs uppercase tracking-wider text-primary-foreground"
              >
                Browse the catalogue
              </Link>
            </div>
          </div>
        </Container>
      </section>

      {/* Discover by mood */}
      <section className="py-20">
        <Container>
          <div className="mb-10 flex items-end justify-between">
            <h2 className="font-display text-3xl">Discover by mood</h2>
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Six accords
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
            {MOODS.map((m) => (
              // 4b will ship `/accords/[slug]`. Until then, point at
              // the filtered list which DOES exist in 4a — preserves
              // intent (browse by mood) without 404s.
              <Link
                key={m.slug}
                href={`/fragrances?accord=${m.slug}`}
                className="group flex aspect-[5/3] items-end justify-between rounded-md border border-border bg-card p-5 transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                <span className="font-display text-2xl">{m.label}</span>
                <span aria-hidden className="font-mono text-xs uppercase tracking-wider opacity-60 group-hover:opacity-100">
                  →
                </span>
              </Link>
            ))}
          </div>
        </Container>
      </section>

      {/* Featured fragrances */}
      <section className="border-t border-border bg-card/60 py-20">
        <Container>
          <h2 className="mb-10 font-display text-3xl">Featured fragrances</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {featured.slice(0, 4).map((f) => (
              <FragranceCard key={f.id} fragrance={f} />
            ))}
            {featured.length >= 6 ? (
              <>
                <div className="hidden lg:block" />
                {featured.slice(4, 6).map((f) => (
                  <FragranceCard key={f.id} fragrance={f} />
                ))}
              </>
            ) : null}
          </div>
        </Container>
      </section>

      {/* Journal teaser placeholder for 4b */}
      <section className="py-20">
        <Container>
          <div className="rounded-lg border border-dashed border-border bg-secondary/30 p-10">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              From the journal
            </p>
            <p className="mt-4 font-display text-2xl">
              Long-form essays on craft, history, and method. <span className="text-muted-foreground">Coming with 4b.</span>
            </p>
          </div>
        </Container>
      </section>
    </>
  );
}
```

### `apps/web/app/(site)/fragrances/page.tsx` (paste-ready skeleton)

```tsx
import { Container } from "@/components/site/Container";
import { FragranceCard } from "@/components/catalog/FragranceCard";
import { FragranceCardSkeleton } from "@/components/catalog/FragranceCardSkeleton";
import { Pagination } from "@/components/catalog/Pagination";
import { FilterSidebar } from "@/components/catalog/FilterSidebar";
import {
  getFragrances,
  getAllAccords,
  type FragranceListParams,
} from "@/lib/api/fetchers";
import { Suspense } from "react";

// Concentration filter facet — fallback static list. There is no
// `/api/v1/concentrations` endpoint in `apps/api/openapi.json` today;
// when one lands, swap this constant for `getAllConcentrations()` and
// move it into Promise.all below.
const CONCENTRATION_FALLBACK = [
  { slug: "edt", name: "EDT" },
  { slug: "edp", name: "EDP" },
  { slug: "parfum", name: "Parfum" },
];

type Search = Record<string, string | string[] | undefined>;

function pickQuery(sp: Search): FragranceListParams {
  // Sort array values for canonical URL+cache keying — see
  // canonicalizeQuery in fetchers.ts.
  const arr = (v: string | string[] | undefined) => {
    const list = Array.isArray(v) ? v : v ? [v] : undefined;
    return list ? [...list].sort() : undefined;
  };
  const num = (v: string | string[] | undefined) =>
    typeof v === "string" ? Number(v) : undefined;
  const str = (v: string | string[] | undefined) =>
    typeof v === "string" ? v : undefined;

  return {
    limit: num(sp.limit) ?? 24,
    offset: num(sp.offset) ?? 0,
    brand: str(sp.brand),
    gender: str(sp.gender) as FragranceListParams["gender"],
    year_min: num(sp.year_min),
    year_max: num(sp.year_max),
    concentration: str(sp.concentration),
    accord: arr(sp.accord),
    note: arr(sp.note),
    perfumer: arr(sp.perfumer),
  };
}

export default async function FragrancesPage(props: {
  searchParams: Promise<Search>;
}) {
  const sp = await props.searchParams;
  const query = pickQuery(sp);

  // Fetch list + facets in parallel. Accords come from the real API so
  // facet slugs cannot drift from seed data; concentration facet is a
  // static fallback until a `/api/v1/concentrations` endpoint exists.
  const [list, accords] = await Promise.all([
    getFragrances(query),
    getAllAccords(),
  ]);

  // Build a canonical URLSearchParams so multi-value selections sort
  // identically across requests (matches canonicalizeQuery on the
  // fetcher tier).
  const usp = new URLSearchParams();
  const sortedKeys = Object.keys(sp).sort();
  for (const k of sortedKeys) {
    const v = sp[k];
    if (v == null) continue;
    const list = Array.isArray(v) ? [...v].sort() : [v];
    for (const vv of list) usp.append(k, vv);
  }

  return (
    <Container className="py-10 md:py-16">
      <h1 className="mb-10 font-display text-4xl">Fragrances</h1>
      <div className="grid gap-10 md:grid-cols-[16rem_1fr]">
        <FilterSidebar
          pathname="/fragrances"
          searchParams={Object.fromEntries(
            sortedKeys.map((k) => {
              const v = sp[k];
              return [k, Array.isArray(v) ? [...v].sort() : (v ?? "")];
            })
          ) as Record<string, string | string[]>}
          facets={{
            accords,
            brands: [], // Brand facet ships with 4b once `/api/v1/brands` is wired into the catalog filter.
            concentrations: CONCENTRATION_FALLBACK,
          }}
        />
        <section>
          <Suspense fallback={
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <FragranceCardSkeleton key={i} />
              ))}
            </div>
          }>
            {list.data.length === 0 ? (
              <div className="rounded-md border border-dashed border-border p-12 text-center">
                <p className="font-display text-2xl">No matches.</p>
                <p className="mt-2 text-muted-foreground">Try clearing some filters.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
                {list.data.map((f) => (
                  <FragranceCard key={f.id} fragrance={f} />
                ))}
              </div>
            )}
            <div className="mt-12">
              <Pagination
                total={list.pagination.total}
                limit={list.pagination.limit}
                offset={list.pagination.offset}
                hrefBase="/fragrances"
                searchParams={usp}
              />
            </div>
          </Suspense>
        </section>
      </div>
    </Container>
  );
}

// ISR via the fetcher (next: { revalidate: 300 }) — the cache key
// embeds the URL searchParams automatically because the fetcher
// receives them as query params.
```

### `apps/web/app/(site)/fragrances/[slug]/page.tsx` (paste-ready skeleton)

```tsx
import { createHash } from "node:crypto";
import { Container } from "@/components/site/Container";
import { Pyramid } from "@/components/catalog/Pyramid";
import { AccordBadge } from "@/components/catalog/AccordBadge";
import { Glossary } from "@/components/site/Glossary";
import { wrapGlossary } from "@/lib/glossary";
import { getFragranceBySlug } from "@/lib/api/fetchers";

// Editorial typographic hero fallback. Reuses ImageFallback's
// constant-L oklch palette (ADR-0036) so the panel matches the
// card aesthetic, but at hero scale we set the fragrance name in
// large Fraunces so the panel reads as intentional, not "no image".
const HERO_BANDS = [25, 35, 45, 70, 200, 280];

function heroPanelOklch(slug: string): string {
  const h = createHash("sha256").update(slug).digest("hex");
  const band = parseInt(h.slice(0, 2), 16) % 6;
  const jitter = (parseInt(h.slice(2, 4), 16) % 12) - 6;
  return `oklch(0.78 0.06 ${HERO_BANDS[band] + jitter})`;
}

function DetailHeroFallback({
  slug,
  name,
  brandName,
}: {
  slug: string;
  name: string;
  brandName: string;
}) {
  return (
    <div
      role="img"
      aria-label={`${name} (no bottle image available)`}
      className="relative aspect-[3/4] flex flex-col items-center justify-center gap-4 overflow-hidden rounded-md p-8 text-center shadow-md"
      style={{ background: heroPanelOklch(slug) }}
    >
      <span className="font-display font-light text-5xl md:text-7xl tracking-tight text-foreground">
        {name}
      </span>
      <span className="font-mono text-xs uppercase tracking-[0.22em] text-foreground/70">
        {brandName}
      </span>
    </div>
  );
}

export default async function FragranceDetailPage(props: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await props.params;
  const f = await getFragranceBySlug(slug);

  return (
    <Container className="py-12 md:py-20">
      {/* Hero split */}
      <div className="grid gap-12 md:grid-cols-12">
        <div className="md:col-span-5">
          {/* Detail hero uses an EDITORIAL typographic fallback rather
              than ImageFallback's letter-bottom-corner pattern (which
              is sized for cards). Same oklch panel, but the fragrance
              name and brand wordmark fill the slot. When P1+ adds an
              `image_url`, swap to `<Image fill priority />`. */}
          <DetailHeroFallback slug={f.slug} name={f.name} brandName={f.brand.name} />
        </div>
        <div className="md:col-span-7">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
            {f.brand.name}
          </p>
          <h1 className="mt-3 font-display text-5xl leading-[1.05] tracking-tight md:text-6xl">
            {f.name}
          </h1>
          <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
            {f.year_released ? <span>{f.year_released}</span> : null}
            <span>{f.gender}</span>
            {f.concentration ? <span>{f.concentration.name}</span> : null}
            {f.perfumers.length > 0 ? (
              <span className="normal-case tracking-normal">
                Nose:{" "}
                {f.perfumers.map((p, i) => (
                  <span key={p.slug}>
                    {p.name}
                    {i < f.perfumers.length - 1 ? ", " : ""}
                  </span>
                ))}
              </span>
            ) : null}
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            {f.accords.map((a) => (
              <AccordBadge key={a.slug} accord={a} />
            ))}
          </div>
          {f.description ? (
            <p className="mt-8 max-w-xl text-base leading-relaxed text-foreground/90">
              {/* First-mention-per-term wrap (handles ALL 12 terms,
                  case-insensitive, all occurrences past the first per
                  term are left as plain text). */}
              {wrapGlossary(f.description, Glossary)}
            </p>
          ) : null}
        </div>
      </div>

      {/* Pyramid */}
      <section className="mt-20">
        <h2 className="mb-8 font-display text-3xl">
          The <Glossary termKey="top-heart-base">pyramid</Glossary>
        </h2>
        <Pyramid notes={f.notes} />
      </section>

      {/* Articles */}
      <section className="mt-20">
        <h2 className="mb-6 font-display text-2xl">In the journal</h2>
        {f.articles.length === 0 ? (
          <p className="text-muted-foreground">No articles yet.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {f.articles.map((a) => (
              <li key={a.slug} className="font-display text-lg">
                {a.title}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* "More from this brand" placeholder */}
      <section className="mt-20 rounded-lg border border-dashed border-border bg-secondary/30 p-8">
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          More from {f.brand.name}
        </p>
        <p className="mt-2 text-foreground/80">
          Brand pages land in 4b. The list will populate then.
        </p>
      </section>
    </Container>
  );
}
```

### `apps/web/app/(site)/loading.tsx` / `error.tsx` / `not-found.tsx` (skeletons)

```tsx
// loading.tsx
import { Container } from "@/components/site/Container";
import { FragranceCardSkeleton } from "@/components/catalog/FragranceCardSkeleton";

export default function Loading() {
  return (
    <Container className="py-16">
      <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <FragranceCardSkeleton key={i} />
        ))}
      </div>
    </Container>
  );
}
```

```tsx
// error.tsx
"use client";
import { useEffect } from "react";
import { Container } from "@/components/site/Container";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <Container className="py-24 text-center">
      <h1 className="font-display text-4xl">Something went wrong.</h1>
      <p className="mt-4 text-muted-foreground">
        We logged the error. Try again, or browse the catalogue.
      </p>
      <Button className="mt-8" onClick={reset}>Try again</Button>
    </Container>
  );
}
```

```tsx
// not-found.tsx
import Link from "next/link";
import { Container } from "@/components/site/Container";

export default function NotFound() {
  return (
    <Container className="py-24 text-center">
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">404</p>
      <h1 className="mt-3 font-display text-5xl">Not in the catalogue — yet.</h1>
      <p className="mt-6 text-muted-foreground">
        Either the URL is off, or this fragrance hasn’t been added.
      </p>
      <Link href="/fragrances" className="mt-8 inline-block font-mono text-xs uppercase tracking-wider text-accent underline">
        Browse fragrances
      </Link>
    </Container>
  );
}
```

### `apps/web/app/sitemap.ts` (paste-ready)

```ts
import type { MetadataRoute } from "next";
import { getFragrances } from "@/lib/api/fetchers";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://fragwise.app";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Page through results: API caps `limit` at 100 (see openapi.json
  // schema for /api/v1/fragrances; `next build` would 422 if we sent
  // a larger value). FragranceListItem does NOT carry an `updated_at`
  // field today, so we use the build-time `Date.now()` as
  // `lastModified` for every fragrance entry. When P1+ adds an
  // `updated_at` (or equivalent) column, swap in `f.updated_at`.
  const all: Array<{ slug: string }> = [];
  let offset = 0;
  const PAGE = 100;
  // R3 fix: hard cap iterations to prevent an infinite build hang if
  // the API ever lies about pagination.has_next or returns the same
  // offset repeatedly. 200 iterations × 100 = 20k slugs is far above
  // the OSS catalog ceiling.
  const MAX_PAGES = 200;
  for (let i = 0; i < MAX_PAGES; i += 1) {
    const list = await getFragrances({ limit: PAGE, offset });
    if (list.data.length === 0) break; // empty page guard
    all.push(...list.data.map((f) => ({ slug: f.slug })));
    if (!list.pagination.has_next) break;
    offset += PAGE;
  }

  const lastModified = new Date();

  return [
    { url: `${SITE}/`, lastModified, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE}/fragrances`, lastModified, changeFrequency: "daily", priority: 0.9 },
    ...all.map(({ slug }) => ({
      url: `${SITE}/fragrances/${slug}`,
      lastModified,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
  ];
}

export const revalidate = 3600;
```

### `apps/web/app/robots.ts` (paste-ready)

```ts
import type { MetadataRoute } from "next";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://fragwise.app";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/" }],
    sitemap: `${SITE}/sitemap.xml`,
  };
}
```

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Unit (vitest) | `FragranceCard` renders brand/name/year/gender; focus ring class present | Render with sample list item; assert text + class |
| Unit | `ImageFallback` color determinism | Render twice with same slug; compare inline `style.backgroundColor`; render with different slug to assert variance |
| Unit | `Pyramid` populated AND missing role | Render with three roles populated; render with empty heart; assert `—` placeholder |
| Unit | `Pagination` boundary disable | Mount with `offset=0` (assert prev disabled), then `offset+limit>=total` (assert next disabled) |
| Unit | `Glossary` tooltip presence | Render wrapper; assert dotted-underline class + Tooltip role |
| Unit | `getFragranceBySlug` cache options | Mock `apiClient.GET`; assert it's called with `next.revalidate=600` and `tags` containing `fragrance:s` |
| Integration | Page tests via `next/server` test harness | Defer to Playwright |
| E2E (Playwright, manual trigger) | `home.spec.ts` — brand + featured strip | `expect(page.getByText('Fragwise')).toBeVisible(); expect(page.getByRole('heading', {name: /featured fragrances/i})).toBeVisible()` |
| E2E | `fragrances.spec.ts` — pagination + filter | Click page 2, assert URL contains `offset=`; click an accord, assert URL contains `accord=` and grid count changes |
| E2E | `fragrance-detail.spec.ts` — pyramid renders | Visit a known slug, assert `TOP`/`HEART`/`BASE` labels visible |
| Static | TypeScript | `tsc --noEmit` clean as part of CI |
| Static | API types stale check | `git diff --exit-code apps/web/lib/api/types.ts` after regen in CI |
| Visual / a11y | Manual pre-merge | Keyboard tab order, focus ring visibility, `axe` browser pass on home + list + detail |

## Cross-Cutting Concerns

### Bundle budget

Target: **≤ 220 KB initial JS gzipped** for `/` and `/fragrances`,
enforced in CI by `size-limit`. The judgment-day pass flagged the
original 200 KB target as unrealistic with Radix peer-deps; 220 KB is
defensible while still rejecting drift. Two reinforcements:

1. **CI enforcement (size-limit)**. Add `size-limit` (`^11`) and
   `@size-limit/preset-app` to `apps/web/package.json` devDeps. Add a
   `.size-limit.json` config:

   ```jsonc
   // R3 fix: paths are relative to apps/web (where pnpm exec runs cwd),
   // and DO NOT include the (site) route group — Next.js erases route
   // groups from the on-disk chunk path. Verify by inspecting
   // .next/static/chunks/app/ after `next build`.
   [
     {
       "name": "/ (home, initial JS)",
       "path": ".next/static/chunks/app/page-*.js",
       "limit": "220 KB",
       "gzip": true
     },
     {
       "name": "/fragrances (list, initial JS)",
       "path": ".next/static/chunks/app/fragrances/page-*.js",
       "limit": "220 KB",
       "gzip": true
     }
   ]
   ```

   Add a CI step in `.github/workflows/web.yml` that runs after build:
   `pnpm --filter web exec size-limit`. CI fails on threshold breach.
   **Apply-phase MUST verify** the chunk paths exist after the first
   `next build` (the route-group elision is undocumented in Next.js
   release notes; if a future Next version re-emits `(site)`, update
   the globs).

2. **Lazy-import non-server-rendered Radix consumers** to keep above-
   the-fold JS small. The mobile menu is the obvious target — its
   sheet primitive only mounts on a click event. In `Header.tsx`:

   ```tsx
   import dynamic from "next/dynamic";
   const MobileMenu = dynamic(
     () => import("./MobileMenu").then((m) => m.MobileMenu),
     { ssr: false }
   );
   ```

   The Glossary popover is also a candidate if the detail page ever
   pushes over budget (defer until measured).

3. **Font-weight trim**. If the budget still strains, drop one weight
   in this order: JetBrains Mono `500` (mono labels rarely need a
   medium); next, Manrope `700` (use 600 for emphasis). Fraunces 400/
   500/600 stay — display variation drives the editorial feel.

Known cost contributors:
- `openapi-fetch`: ~6 KB
- shadcn primitives (10 added): ~25–35 KB total when actually rendered
- Three font families (Fraunces + Manrope + JetBrains Mono, limited
  weights, latin subset only): ~250 KB **of font payload**
  (separate from JS budget). Mitigations: `display: 'swap'`, latin only,
  pre-connect via `next/font` automatic.
- `lucide-react`: tree-shaken per icon (~1 KB per icon used).

Out-of-budget (deliberately deferred): `framer-motion`, `react-markdown`
(4b only), TanStack Query.

### Image strategy

- `next/image` with `remotePatterns` for `images.fragwise.app` (R2
  CDN — confirm hostname).
- `ImageFallback` is the rendered path for every fragrance in 4a since
  the P1 contract has no `image_url` field today. The conditional swap
  in `FragranceCard` is left in place for the day P1+ adds the column.
- Fragrance hero on detail uses `priority` only when `image_url` exists
  (currently never).
- `quality={75}` default; `sizes` set per breakpoint as shown.

### Accessibility baseline (WCAG 2.1 AA)

- `SkipToContent` first focusable in `(site)/layout.tsx`.
- All shadcn primitives are Radix-based: keyboard + screen reader
  support out of the box for `tooltip`, `accordion`, `sheet`,
  `pagination`, `select`, `popover`.
- Focus ring contract in `globals.css`: `outline: 2px solid
  var(--color-ring)` on every focusable.
- Color contrast verified: foreground vs background ≥ 7:1 (AAA);
  muted-foreground vs background ≥ 4.5:1 (AA); accent-on-background ≥
  3:1 (large-text AA, used only on large text and chips).
- `<input disabled>` search bar has `aria-label="Search (coming soon)"`.
- `ImageFallback` uses `role="img"` + descriptive `aria-label`.
- Logical heading order: one `<h1>` per page; `<h2>` for sections.
- `next-themes` renders `suppressHydrationWarning` on `<html>` (already
  in P0b).

### Search bar disabled state

- Input is rendered with `disabled` attribute and placeholder `Search
  coming soon`. Cursor: default (not text). No tooltip in 4a (touch
  users can't trigger it on a disabled input). When P2 ships, the
  same input element gains an `onChange` and `disabled` is dropped.

## Migration / Rollout

- 4a is purely additive in `apps/web/`. No DB, no API, no ontology
  changes.
- Pre-merge: `git reset` is sufficient.
- Post-merge / pre-deploy: revert merge commit; web has not deployed.
- Post-deploy: redeploy prior Vercel build.
- Cache: ISR keys are URL-based; on first deploy of 4a, all keys are
  cold. No data migration required.

## Judgment-Day Pass — Fixes Log

This design absorbed two rounds of judgment-day adversarial review.
Confirmed defects were fixed in place above; suspect findings were
verified against the design source and either fixed or dismissed
with rationale.

### Confirmed (fixed in place)

- **C1 — Sitemap `limit: 1000` violates OpenAPI `maximum: 100`.**
  `app/sitemap.ts` rewritten to page through results with `PAGE=100`
  using the `pagination.has_next` flag. ADR-0040 updated.
- **C2 — Glossary `description.split("sillage")` drops content past
  index 1 and only handles 1 of 12 terms.** Replaced with
  `wrapGlossary(text, Glossary)` helper in `lib/glossary.tsx`.
  Detail page calls `wrapGlossary(f.description, Glossary)`.
- **C3 — Glossary tooltip doesn't trigger on touch.** `Glossary.tsx`
  switched from Radix `Tooltip` to `Popover` (click/tap + keyboard).
  ADR-0039 updated; spec narrative remains satisfied (the spec phrasing
  "Radix `Tooltip` long-press OR EQUIVALENT" leaves room for Popover).
  No spec change required; if reviewers want stricter conformance, the
  spec can later be normalised to "popover" wording.
- **C4 — Light theme missing `color-scheme: light` declaration.** Added
  to `:root` in `tokens.css` AND surfaced via `viewport.colorScheme: 'light'`
  in `app/layout.tsx`. ADR-0037 updated.
- **C5 — Pagination disabled controls keyboard-activatable + invalid
  HTML.** Disabled boundaries render `<span aria-disabled>`, not
  `<a href="#">`. Adjacent items wrapped in `<React.Fragment>` instead
  of a `<span>` so the DOM is `<ul><li>...</li></ul>` (valid).
- **W1 — Dead links to 4b routes.** Mood tiles point at
  `/fragrances?accord=<slug>` (works in 4a). Header `NAV` placeholder
  items render as `<span aria-disabled>` non-interactive labels;
  `MobileMenu` threads the placeholder flag.
- **W2 — Multi-value filter cache fragmentation.** `canonicalizeQuery`
  in `fetchers.ts` sorts array params before fetch; `pickQuery` in the
  list page sorts on the URL side too.
- **W3 — `GenderIcon` and `lib/format.ts` not in component inventory.**
  Inlined a `genderIcon()` switch in `FragranceCard.tsx` using
  `lucide-react` (`Mars`, `Venus`, `CircleDot`). `lib/format.ts`
  removed from the file inventory.
- **W4 — FilterSidebar hardcoded slugs.** List page now
  `Promise.all`'s `getFragrances(...)` + `getAllAccords()`. Real
  accord facets passed in. `/api/v1/concentrations` does NOT exist
  (verified against `apps/api/openapi.json`); concentration filter
  uses a static fallback list (EDT/EDP/Parfum) and is documented as a
  follow-up that will add the endpoint.
- **W5 — ImageFallback contrast fails AA on 4 of 6 bands.** Switched
  from HSL to oklch with constant `L=0.78`; foreground is dark ink
  universally. ADR-0036 updated.
- **W6 — Bundle budget unrealistic + lazy-imports.** Target raised
  from 200 to 220 KB gzipped initial JS, enforced by `size-limit` in
  CI (config + workflow step added). `MobileMenu` lazy-imported via
  `next/dynamic`. ADR-0033 updated.

### Suspect (verified — outcome documented)

- **S1 — FilterSidebar passes `URLSearchParams` across server/client
  boundary + missing `"use client"`.** **CONFIRMED REAL** (FilterSidebar
  uses Radix `Accordion` which requires a Client Component, and the
  prop signature took a `URLSearchParams` instance that does not
  serialize). **FIXED**: `"use client"` added; prop signature changed
  to `Record<string, string | string[]>`; list page converts via
  `Object.fromEntries(...)` before passing. URLSearchParams is
  reconstructed lazily inside the component for href building.
- **S2 — CI staleness gate is half-blind.** **CONFIRMED REAL** (the
  original web.yml step regenerated `types.ts` from a possibly-stale
  committed `openapi.json`, so `git diff` could pass while runtime
  drifted). **FIXED**: web.yml now also runs `emit_openapi.py` and
  `git diff --exit-code apps/api/openapi.json` upstream of the
  types-stale check. Matches the existing api.yml gate.
- **S3 — `aria-pressed` on `<Link>` is invalid.** **CONFIRMED REAL**
  (FilterSidebar set `aria-pressed` on Next.js `<Link>` which renders
  to `<a>`; `aria-pressed` is for buttons). **FIXED**: replaced with
  `aria-current="true"` on active filter links.
- **S4 — `panelHsl` uses `node:crypto`.** **CONFIRMED REAL** (the
  module imports `node:crypto`). **FIXED via documentation**: comment
  added to `ImageFallback.tsx` and ADR-0036 explaining that the Node
  runtime is intentional and that an Edge migration would swap for
  `crypto.subtle.digest`. No code change today since 4a does not pin
  Edge runtime on any `(site)` route.
- **S5 — `getFragrances` data envelope can be undefined.**
  **CONFIRMED REAL** (the `data` field from `openapi-fetch` is
  `T | undefined`; the original code returned it unchecked).
  **FIXED**: `getFragrances` throws on `!data`; `getFragranceBySlug`
  calls `notFound()` on `!data` after the existing 404/error checks.
- **S6 — Detail hero is always ImageFallback (no images yet).**
  **CONFIRMED REAL** (the original detail page rendered
  `<ImageFallback />` unconditionally, using a card-scaled
  letter-in-the-corner). **FIXED**: introduced `DetailHeroFallback`
  inline in the detail page — same oklch panel, but the fragrance
  name + brand wordmark fill the slot in large Fraunces. ADR-0036
  notes the typographic hero variant.

### Verification notes (sections read)

- ADR-0033 (Editorial-perfumery) — read; budget revision appended.
- ADR-0036 (ImageFallback hash) — read; rewritten to oklch + constant L.
- ADR-0037 (Light theme only) — read; native widget commitment appended.
- ADR-0039 (Glossary tooltip pattern) — read; rewritten to Popover.
- ADR-0040 (Sitemap and robots) — read; rewritten to paginated fetch.
- `app/sitemap.ts` snippet — read; rewritten.
- `app/layout.tsx` snippet — read; viewport + meta added.
- `styles/tokens.css` `:root` block — read; `color-scheme: light` added.
- `lib/api/fetchers.ts` (entire snippet) — read; canonicalize +
  not-found + accords helper added.
- `components/site/Glossary.tsx` snippet — read; rewritten to Popover.
- `components/site/Header.tsx` snippet — read; placeholder rendering +
  dynamic import added.
- `components/site/MobileMenu.tsx` snippet — read; placeholder flag
  threaded.
- `components/catalog/FragranceCard.tsx` snippet — read; GenderIcon
  inlined.
- `components/catalog/ImageFallback.tsx` snippet — read; oklch
  rewrite.
- `components/catalog/Pagination.tsx` snippet — read; disabled-span
  + Fragment refactor.
- `components/catalog/FilterSidebar.tsx` snippet — read; client
  directive + serializable props + aria-current.
- `app/(site)/page.tsx` snippet — read; mood tiles re-pointed.
- `app/(site)/fragrances/page.tsx` snippet — read; real-facet fetch +
  serializable prop conversion.
- `app/(site)/fragrances/[slug]/page.tsx` snippet — read; typographic
  hero + wrapGlossary.
- `apps/api/openapi.json` — read; confirmed `limit.maximum=100`,
  `/api/v1/accords` exists with no pagination, `/api/v1/concentrations`
  does NOT exist, `FragranceListItem` has no `updated_at`.
- `.github/workflows/api.yml` — read; existing emit-openapi gate
  confirmed (mirrored into web.yml).
- spec `web-app/spec.md` (Glossary requirement) and
  `fragrance-catalog-ui/spec.md` (Glossary requirement) — read; the
  "Radix `Tooltip` long-press OR EQUIVALENT" wording covers Popover,
  no spec rewording required for this iteration.

## Open Questions

- [ ] **R2 hostname confirmation.** `next.config.ts` uses
  `images.fragwise.app` based on the proposal's "Phase 0c R2 hostname
  must be confirmed". If 0c picked a different host (e.g. an
  `*.r2.dev` URL or a different custom domain), update the
  `remotePatterns` entry. This is a one-line change.
- [ ] **Featured fragrance source.** No `featured=true` flag in P1's
  contract. 4a uses "first 6 in default order". Acceptable
  placeholder per proposal scope; revisit when P5 adds curation.
- [ ] **Year-range slider.** API params (`year_min` / `year_max`) are
  wired in the fetcher; 4a renders the year accordion as info-only
  text. Slider control is deferred to 4b unless promoted in
  `judgment-day` review.
- [ ] **`AccordBadge` vs `AccordChip` rendering on `FragranceCard`.**
  4a's card omits accord chips for visual sparseness; the detail page
  carries them. Confirm in `judgment-day` whether the list card should
  surface up to 1 lead accord.
- [ ] **GitHub repo URL** — `Footer.tsx` references
  `https://github.com/Iam2Fast/fragwise`; confirm or replace with the
  canonical org/repo before `sdd-apply`.
- [ ] **`/api/v1/concentrations` endpoint** — does NOT exist in the
  current `apps/api/openapi.json`. The concentration filter facet
  uses a static fallback list (EDT/EDP/Parfum). Track a follow-up
  P1.x change that adds the endpoint and swaps the fallback for a
  `getAllConcentrations()` fetch in `fragrances/page.tsx`.

---

## Known Follow-ups for Apply Phase (R3 — judgment-day carry-over)

Round 3 of judgment-day surfaced these. The 3 CRITICALs were fixed
inline in the design (wrapGlossary regex, sitemap upper bound,
duplicate `color-scheme` meta). The smaller items below are best
caught when actual code runs (`next build`, `next dev`, `vitest`,
Playwright). Each has a precise diagnosis and a recommended fix.

### F1 — Verify `size-limit` glob matches real chunk paths

After the first `next build` in apply, `ls apps/web/.next/static/chunks/app/` and confirm `page-*.js` is at the top level (route group `(site)` erased) and `fragrances/page-*.js` exists. If any path differs, update `.size-limit.json`. The CI gate fails LOUD when no files match — this is the most likely place a misalignment will surface.

### F2 — Verify mood tile slugs match seeded accord taxonomy

`MOODS` in `app/(site)/page.tsx` hardcodes `fresh, woody, floral, gourmand, oriental, aquatic`. After `just ingest && just seed`, run `psql` (or a quick fetcher script) to list `accords.slug` and confirm all 6 mood slugs are present. If any are missing (e.g. seed uses `oud-woody` instead of `woody`), either update the mood list to match or add the missing accord rows in seed data. Without this, mood tiles silently 0-result.

### F3 — Confirm concentration filter slugs

The concentration accordion uses a static `CONCENTRATION_FALLBACK = [{slug:"edt"},{slug:"edp"},{slug:"parfum"}]`. The catalog API accepts any string for `?concentration=`. Run a smoke fetch `GET /api/v1/fragrances?concentration=edt` against the seeded DB; if it returns rows, the slugs match. If empty, inspect the actual concentration slugs the seed produced (likely `eau-de-toilette`, `eau-de-parfum`, `extrait`) and update the fallback list. Alternatively, hide the concentration accordion entirely until P1.x ships `/api/v1/concentrations`.

### F4 — Add `getAllBrands()` or remove the brand accordion

`facets.brands` is currently `[]` in `fragrances/page.tsx`. The Brand accordion will render an empty open container — visual artifact. Either:
- (a) add `getAllBrands()` to `lib/api/fetchers.ts` (mirror of `getAllAccords`) and thread it through `Promise.all` to populate `facets.brands`, or
- (b) drop the Brand accordion from FilterSidebar entirely until 4b.

Recommend (a); brands API exists per OpenAPI.

### F5 — DetailHeroFallback overflow on long names

`DetailHeroFallback` renders the fragrance name at `text-5xl md:text-7xl` with no `break-words`/`hyphens-auto`. Long names like "L'Air du Désert Marocain" will clip horizontally inside the `aspect-[3/4]` container with `overflow-hidden`. Test with the longest name in seed data; if clipping is visible, add `break-words leading-[0.95] text-balance` and consider `clamp(2rem, 6vw, 4.5rem)` font sizing.

### F6 — `pickQuery` should validate gender + year ranges

`pickQuery` casts `?gender=foo` and `?year_min=1066` directly into the request — API returns 422 → page error. Add narrow validation:
- `gender`: only allow values in `["masc","fem","unisex","genderfree"]`; otherwise drop.
- `year_min` / `year_max`: clamp to `[1700, 2100]`; out-of-range values dropped.

This prevents hand-typed bad URLs from crashing the page.

### F7 — `aria-current="page"` over `aria-current="true"` on FilterSidebar links

Cosmetic ARIA hygiene. Replace the four `aria-current="true"` declarations on `<Link>` filter chips with `aria-current="page"` (or accept `true` as adequate — JAWS/NVDA both announce it).

### F8 — Spec text drift: Glossary "tooltip" wording

`specs/fragrance-catalog-ui/spec.md` Requirement "Glossary Tooltip Wrapper" still uses "tooltip" 6 times after the design switched to `Popover`. The spec wording "Radix `Tooltip` long-press OR EQUIVALENT" technically permits Popover, but a strict spec verifier will flag drift. At archive time, rename the requirement to "Glossary Popover Wrapper" and update scenario language to "popover". Same for `web-app/spec.md` Requirement "Glossary Tooltips On Jargon" — drop the hover requirement since Popover requires click/tap.

### F9 — `loading.tsx` vs in-page `<Suspense>` redundancy

The fragrances page wraps the grid in `<Suspense fallback={...}>` but the data fetch happens before the boundary, so the Suspense fallback never triggers. Either move the fetch into a suspended child component, or drop the in-page `<Suspense>` and rely solely on `loading.tsx`. Recommend the latter — simpler.

### F10 — Glossary `cursor-help` misleading on click trigger

The Popover trigger uses `cursor-help` (question-mark cursor), implying hover-for-info. Since the trigger now requires a CLICK to open, change to `cursor-pointer`.

### F11 — Inconsistent error contract: `getFragrances` throws, `getFeaturedFragrances` returns `[]`

Pick one. Recommend throwing in both and rendering an empty/error state at the page level so UX is honest about failures.

### F12 — Spec mismatch: `web-app` MODIFIED requirement says "links MAY 404"

Now that mood tiles point at `/fragrances?accord=<slug>` (which always 200s in 4a), tighten the spec to "links MUST resolve to 200 in 4a, either via 4b routes or via `/fragrances?accord=`". Cosmetic.

### F13 — Verify `GenderIcon` lucide-react icons exist

Apply uses `Mars`, `Venus`, `CircleDot` from lucide-react. Verify these are valid exports in the installed lucide-react version (they should be; standard lucide names). If renamed/removed, swap.

---

**Bottom line for the implementer**: F1, F2, F3, F4 are the items that will visibly break the UI on first run. F5-F13 are lower priority; surface them via `next build` warnings, vitest failures, or manual a11y inspection.

---

## Return Envelope

**Status**: success
**Executive summary**:
Phase 4a design captures HOW the web spine implements three pages
(`/`, `/fragrances`, `/fragrances/[slug]`), a typed `openapi-fetch`
client over the now-locked `apps/api/openapi.json`, an editorial-perfumery
design system (Fraunces + Manrope + JetBrains Mono, ivory/ink/sepia
oklch palette, asymmetric layouts) sourced from the `frontend-design`
skill (ADR-0033), URL-driven filters + pagination, deterministic
SHA-256-derived ImageFallback panels (ADR-0036), 12-term Glossary
tooltips, ISR-by-default caching with cache tags, sitemap+robots, and
a CI gate that blocks stale generated types. 8 ADRs (0033–0040)
document each decision. All paste-ready skeletons (tokens.css, layout
fonts, client, fetchers, components, pages) are included so
`sdd-tasks` can split work cleanly. **`judgment-day` review of THIS
design is REQUIRED before `sdd-tasks` (Process Gates section).**

**Artifacts**:
- `openspec/changes/phase-4a-web-spine/design.md`

**Next recommended**: `judgment-day` adversarial review of design.md
(blocking gate). On pass → `sdd-tasks: phase-4a-web-spine`. After
tasks → `sdd-apply`.

**Risks**:
- R1 (R2 hostname mismatch — Open Question, 1-line fix)
- R2 (featured source is a list-default placeholder until P5)
- R3 (font payload ~250 KB — mitigated by latin subset + display swap)
- R4 (P1 contract has no `image_url` today — fallback IS the path; if
  P1+ later adds it, FragranceCard's conditional swap activates with
  no further design change)
- R5 (judgment-day may push back on visual sparseness of FragranceCard
  — design accepts iteration there)
