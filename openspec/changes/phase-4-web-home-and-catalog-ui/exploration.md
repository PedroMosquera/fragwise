# Exploration: phase-4-web-home-and-catalog-ui

> Investigation only — no design, no code, no visual decisions locked. The
> orchestrator decides what to lock into `proposal.md` / `design.md`.

## Current State (post 0a/0b/0c, in parallel with 1/2)

- `apps/web/` is a Next.js 16.2.2 + Tailwind v4 + shadcn skeleton scaffolded
  in 0b. Today it renders a single placeholder home page (`<h1>Fragwise</h1>`
  + a `Coming soon` shadcn `<Button disabled>`) — no nav, no header, no
  footer, no other routes.
- `apps/web/app/layout.tsx` already wires `next-themes` `ThemeProvider`
  (class-based, system default, transition disabled), the `Inter`
  google-font (loaded via `next/font/google`, `--font-inter` CSS var), and
  the `sonner` toaster.
- `apps/web/components/ui/` has 10 shadcn primitives installed:
  `badge`, `button`, `card`, `dialog`, `dropdown-menu`, `input`, `label`,
  `separator`, `sonner`, `tabs`. No `sheet`, no `tooltip`, no
  `accordion`, no `command`, no `navigation-menu`, no `skeleton`,
  no `popover`, no `scroll-area`, no `breadcrumb`, no `select`,
  no `pagination` — all of which Phase 4 likely wants.
- `apps/web/lib/` exists (presumably with `cn()`/utils) but no API client,
  no fetcher, no schemas/types.
- `apps/web/next.config.ts` has only `reactStrictMode: true`. **No
  `images.remotePatterns`** for R2 or any other host. Image rendering
  outside `next/image` works, but `next/image` will reject any non-localhost
  src until configured.
- `apps/web/__tests__/` has at least one render test (per the `web-app`
  spec smoke requirement). E2E `home.spec.ts` asserts `"Fragwise"` is
  visible — it will need an update if the home hero changes copy.
- Phase 1 (catalog-read endpoints) and Phase 2 (hybrid search) are
  **in flight, not yet shipped**. Phase 1's exploration recommends a
  committed `apps/api/openapi.json` with a `just openapi-export` recipe
  and CI drift check. Phase 4 is a downstream consumer of that file.
- The Phase 1 exploration recommends: `/api/v1/` prefix; offset+limit
  pagination with envelope `{data, pagination: {total, limit, offset}}`;
  slug-based URL path segments and slug-based filter values; gender as
  a 4-value ENUM (`masc|fem|unisex|genderfree`); nested-by-endpoint
  response shape (lists slim, details fat); 404 with
  `{"detail": "..."}`; `Cache-Control: public, max-age=60,
  stale-while-revalidate=300` on read endpoints. **None of those are
  locked yet** — they're recommendations awaiting the user's decisions
  in `phase-1-catalog-read-endpoints/proposal.md`.
- Phase 2's hybrid-search endpoint is similarly out — Phase 4's search bar
  must be a placeholder.
- `data/seed/` (post 0c) has fragrance/brand/perfumer/note/accord/article
  rows. **Most fragrances have no real bottle image**; image columns are
  largely empty (R2 production bucket is set up but unfilled). Phase 4's
  visual layout must look intentional with image-less cards as the common
  case.
- License: Apache-2.0; portfolio-grade OSS project. The user explicitly
  flagged "generic AI design slop" as the worst-case outcome.

## Affected Areas

This change is purely additive in `apps/web/` (no changes to API, ontology,
or data scripts).

- `apps/web/app/` — **all 13 new route directories** (home is overwrite,
  the other 12 are net-new). Each new route gets `page.tsx`, optionally
  `loading.tsx`, optionally `error.tsx`, and detail routes use dynamic
  `[slug]/page.tsx`.
- `apps/web/app/layout.tsx` — wrap children with new `<SiteHeader>` /
  `<SiteFooter>`. Possibly add a font swap (current Inter is the AI-default
  flag). Add a skip-to-content link.
- `apps/web/app/globals.css` — extend the `@theme` block with
  Fragwise-specific tokens (palette, typography, spacing, radius). Today
  it's a bare `@import "tailwindcss"` plus a comment.
- `apps/web/components/` — **new** site-level components: `site-header`,
  `site-footer`, `fragrance-card`, `note-badge`, `accord-badge`,
  `pagination`, `filter-sidebar`, `breadcrumbs`, `bottle-image` (next/image
  wrapper with placeholder fallback), `glossary-tooltip`, `notes-pyramid`,
  `markdown` (article renderer).
- `apps/web/components/ui/` — **add shadcn primitives** likely needed:
  `sheet` (mobile drawer), `tooltip` (glossary terms), `accordion`
  (filter groups), `command` (search palette stub), `skeleton`
  (loading), `popover`, `scroll-area`, `breadcrumb`, `select`,
  `navigation-menu` (or hand-rolled). Decide which of these we actually
  ship in 4.
- `apps/web/lib/api/` — **new**: generated `paths` types from
  `openapi-typescript`, a thin `openapi-fetch` client (or `fetch` wrapper
  + zod), and per-resource read helpers.
- `apps/web/lib/` — `format.ts` (year, gender pretty), `slug.ts` (if any
  client-side slug usage), `placeholders.ts` (no-image fallback).
- `apps/web/next.config.ts` — add `images.remotePatterns` for the R2
  public CDN host (and localhost during dev for placeholder paths).
- `apps/web/package.json` — possibly: `openapi-typescript` (devDep),
  `openapi-fetch` (dep), `react-markdown` + `remark-gfm` (article
  rendering), `@tanstack/react-query` (if we go that route). All of these
  add to bundle / install size; weigh below.
- `apps/web/__tests__/` — render tests for each new shared component.
- `apps/web/e2e/home.spec.ts` — update assertion if hero copy moves.
- `openspec/specs/web-app/spec.md` — major delta. The current spec is
  scaffold-only (toolchain). Phase 4 graduates it from "scaffold" to
  "Fragwise's catalog UX." The spec needs requirements for: route map,
  shared layout components, fragrance card contract, image fallback
  contract, accessibility floor, performance budget.
- `justfile` — likely add `web-openapi-types` recipe that runs
  `openapi-typescript apps/api/openapi.json -o apps/web/lib/api/types.ts`.
  Phase 1 will own the `openapi-export` half.

## Sub-area 1 — API client and data fetching

### Unknowns

#### U-Data-1. Generated typed client: `openapi-typescript` + `openapi-fetch` vs alternatives
Three viable shapes verified via Context7 (`/openapi-ts/openapi-typescript`):

1. **`openapi-typescript` (types only) + a hand-written `fetch` wrapper.**
   - `openapi-typescript apps/api/openapi.json -o lib/api/types.ts` emits a
     ~runtime-free `paths` type tree.
   - Hand-written wrapper: `async function api<P extends keyof paths>(...)`.
   - Pros: zero runtime deps, smallest bundle, full control over caching
     headers and Next.js `next: { revalidate, tags }` options per call.
   - Cons: ~50 LOC of wrapper boilerplate, you re-derive what
     `openapi-fetch` already gives.

2. **`openapi-typescript` + `openapi-fetch`.** (~6 KB runtime per
   Context7 docs, dated current.)
   - `createClient<paths>({ baseUrl })` returns a typed `client.GET`,
     `client.POST` etc. with `data | error` discriminated unions.
   - Pros: tiny, type-driven, no codegen tax, plays cleanly with Next.js
     `fetch` semantics — `openapi-fetch` is a thin wrapper around the
     native `fetch` so `cache`, `next.revalidate`, `next.tags` pass
     through. Confirmed in Context7's "Next.js Server-Side Fetching"
     example.
   - Cons: one more dep to track; minor mismatch if API shapes have
     unusual semantics (rare for a clean OpenAPI 3.1 spec from FastAPI
     0.128).

3. **`hey-api/openapi-ts` (heavier codegen, generates classes/SDK).**
   - Pros: full SDK with model classes; popular alternative.
   - Cons: heavier output, more opinionated, harder to tree-shake. Less
     idiomatic for a simple read-only client.

**Tentative recommendation: option 2 — `openapi-typescript` (devDep) +
`openapi-fetch` (runtime).** The 6 KB cost is negligible against the
bundle budget, the typed-`data | error` shape forces 4xx handling at
the call site, and Next.js `fetch` extensions are first-class.

#### U-Data-2. Where to fetch — RSC vs client + TanStack Query
Per Context7's Next.js 16 docs the `fetch` extension is built for RSC:
`{ cache: 'force-cache' | 'no-store' }` and `{ next: { revalidate, tags } }`
give us SSR + ISR + on-demand revalidation **with no runtime cache
library**.

| Approach | Pros | Cons |
|---|---|---|
| **RSC-only fetching** (`async` server components) | Zero client-side cache code; SEO-perfect (SSR HTML); TanStack-Query-free bundle; Next.js handles dedupe + tag-based revalidation | No client-side optimistic updates; no easy retry/refetch; client interactivity (filter form -> URL) needs a different mental model |
| **TanStack Query everywhere** (`'use client'` pages with `useQuery`) | Familiar; rich devtools; optimistic mutations (irrelevant Phase 4 — we have no writes); easy retry | Adds ~16 KB gzipped + provider boilerplate; SEO needs hydration; doubles cache layer alongside Next's fetch cache; bigger initial JS bundle |
| **Hybrid: RSC for page-load data, RQ for in-page interactions** | Best of both: SEO + cheap nav, plus optimistic UX where it matters | More architectural surface; "where does this data live?" question on every component |

For Phase 4 there are **no writes** and only one piece of true client
interactivity (filter sidebar, which can use URL search params + RSC
re-render via `searchParams` prop). Search and chatbot are deferred.

**Tentative recommendation: RSC-only.** Server components fetch through
`openapi-fetch`, leaning on Next.js's per-fetch `revalidate` / `tags`.
Filter UI uses URL `searchParams` (read in the server component), which
gives us shareable URLs + SSR result pages for free. Skip TanStack
Query in Phase 4. Revisit when Phase 3 (chatbot) lands — that has
streaming + state and is the natural place to introduce a client cache
if at all.

#### U-Data-3. Caching strategy per page type
Per Phase 1's `Cache-Control: max-age=60, stale-while-revalidate=300`,
the API is already CDN-friendly. Next.js `fetch` revalidation overlays
on top of that. Recommended posture per page:

| Page | Strategy | Rationale |
|---|---|---|
| `/` (home) | `next: { revalidate: 600 }` (10 min ISR) + tagged | Featured fragrances, accord teaser, recent articles all change rarely |
| `/fragrances` (list with filters) | server component reading `searchParams`; `next: { revalidate: 300 }` keyed by URL | Filter combinations are URL-driven; same URL → same cached HTML for 5 min |
| `/fragrances/[slug]` | `next: { revalidate: 600 }` + `tags: ['fragrance:<slug>']` | Detail page changes when a single fragrance is edited |
| `/notes`, `/accords`, `/brands`, `/perfumers` | `next: { revalidate: 1800 }` | Taxonomy is near-static |
| `/notes/[slug]`, `/accords/[slug]`, `/brands/[slug]`, `/perfumers/[slug]` | `next: { revalidate: 600 }` + tags | Same rationale as fragrance detail |
| `/articles`, `/articles/[slug]` | `next: { revalidate: 600 }` + tags | Editorial content |

Tags enable on-demand revalidation later (Phase 5 admin tooling) without
changing the Phase 4 code.

**Tentative recommendation: ISR-by-default with the table above; no
`force-dynamic`; no `force-static` either (so on-demand revalidation
stays available).**

#### U-Data-4. Error handling
Three layers: per-fetch (4xx from API), per-route (Next.js `error.tsx`),
global (Next.js root `error.tsx` / `global-error.tsx`).

- 4xx (e.g. 404 from `/fragrances/{slug}`): fetch helper throws or
  returns a typed error; the page component calls Next's
  `notFound()` which renders the closest `not-found.tsx`.
- 5xx / network: throws; caught by `error.tsx` boundary; user sees a
  styled "something went wrong" panel with a retry button.
- Global crash: `app/global-error.tsx` for the worst case (rare).

**Tentative recommendation: one `app/not-found.tsx` (custom 404), one
`app/error.tsx` (route-segment catch-all), one
`app/global-error.tsx` (last-resort), no per-route `error.tsx` files
unless a route has unique recovery semantics. Adding more later is
mechanical.**

### Risks (Data)

- **D-R1 — API contract drift**: if Phase 1's `openapi.json` shape
  changes after Phase 4 is partway done, every page consuming the
  changed model needs touching. **Mitigation**: lock Phase 1's
  `proposal.md` (envelope, slug-vs-id, sort syntax, error shape, list
  vs detail nesting) BEFORE Phase 4 enters `sdd-design`. Track which
  Phase 1 decisions are blocking — see "Hard Gaps" below.
- **D-R2 — `openapi-fetch` + Next.js fetch caching**: `openapi-fetch`
  passes `init` through, including `next: { revalidate, tags }`.
  Confirmed by Context7. Risk: if a future `openapi-fetch` version
  changes that pass-through, our caching silently breaks. **Mitigation**:
  pin `openapi-fetch`; add an integration test that asserts the request
  was cached (mock fetch and check options).
- **D-R3 — RSC + filter sidebar UX**: RSC re-renders on URL change,
  which means clicking a filter chip causes a full server round-trip.
  At ~200 ms per round-trip + skeleton paint, this is acceptable but
  feels slower than client-side filtering. **Mitigation**: use Next.js
  `<Link prefetch>` + the filter form posting via shallow router push,
  with a transition / skeleton during the new RSC render. If it feels
  bad, escalate to a client-component island that calls a route handler
  for the filtered list. Don't introduce TanStack Query just for this.
- **D-R4 — `openapi.json` not yet committed**: Phase 4 cannot generate
  types until Phase 1 emits it. **Mitigation**: tasks must order Phase
  1's openapi-export step before Phase 4's web-openapi-types step. If
  we want Phase 4 to start in parallel, we can stub a tiny hand-written
  `paths` type and replace it with the generated one when Phase 1 lands.

## Sub-area 2 — Design system / aesthetic

### Unknowns

#### U-Design-1. The "AI slop" floor
The user named the worst case explicitly: "modern catchy but not
overwhelming colors," with the styles.refero example as inspiration but
not prescription, and an emphasis on "warm, editorial, low-saturation,
refined." The audience is dual: connoisseurs (want density, detail,
respect for the craft) AND beginners (want approachable, scannable,
non-intimidating). Both must feel welcome.

The `frontend-design` skill (loaded from
`~/.claude/plugins/marketplaces/claude-plugins-official/plugins/frontend-design/`)
explicitly warns against:
- generic fonts (Inter, Roboto, Arial, system fonts) — **we're using
  Inter today**
- cliché color schemes (purple gradients on white) — **we have no
  custom palette today, so default is shadcn neutral**
- predictable layouts and component patterns — **shadcn defaults
  produce these out of the box**

**Tentative recommendation**: invoke the `frontend-design` skill in
`sdd-design` (and again at start of `sdd-apply`) with a brief that
locks the conceptual direction BEFORE writing CSS tokens. The
direction we tentatively lean toward — based on the user's "warm,
editorial, refined" framing and the fragrance subject matter — is
**editorial / perfume magazine**: serif display headlines, refined
sans body, parchment/ivory background tones, deep ink-style text,
small-caps for technical labels, generous negative space, asymmetric
hero compositions. But the design skill should make the bold call;
exploration is not the place to lock the aesthetic.

Three viable directions to enumerate now (the design phase picks one):

1. **Editorial perfumery** — serif headlines (e.g., GT Sectra, Tiempos,
   Canela, EB Garamond), refined sans body (e.g., Söhne, Aktiv Grotesk,
   or a less-overused open source like Geist or Switzer), warm
   off-whites and deep navy/sepia for accents, full-width photography
   when present, stacked metadata strips in serif italic.
2. **Modernist apothecary** — geometric sans-serif everywhere
   (e.g., GT America Mono for labels, Söhne for body, Reckless for
   display contrast), low-chroma earth palette (clay, moss, ash),
   generous spacing, tabular figures for years and concentrations,
   monogram-style brand badges.
3. **Minimal / refined Swiss** — single neutral sans family (perhaps
   Inter Tight or Geist), grid-driven, lots of negative space, accent
   color used sparingly. Lower aesthetic ceiling but lower risk of
   missing.

The user's explicit pick was "warm, editorial, refined" → direction 1
fits best. The `frontend-design` skill will make it specific in design
phase. Either way, **the home page should feel like a magazine cover,
not a SaaS landing**.

#### U-Design-2. Color tokens — palette source
Three options:

1. Pull a palette directly from the `styles.refero` link the user
   referenced (the user said it's an idea, not the final approach).
2. Hand-tune from scratch in design phase, keyed to the chosen
   direction (likely editorial-perfumery).
3. Use a published OKLCH-based palette generator (e.g., Tailwind v4
   `@theme` examples, Radix Colors) and remap.

**Tentative recommendation: option 2.** Hand-tune in design phase. The
refero link should be reference inspiration, not a paste. Tailwind v4
`@theme` blocks with OKLCH values give us perceptually uniform palette
math for free. Plan for tokens: `--color-background`, `--color-surface`,
`--color-border`, `--color-text`, `--color-text-muted`, `--color-accent`,
`--color-accent-soft`, plus 1-2 "category" hues for accord families.

#### U-Design-3. Typography
Today: Inter via `next/font/google`. The design skill flags Inter as
overused. Recommendation: replace with two distinct families.

Options for the display/serif slot (open-source where possible):
- **EB Garamond** (Google Fonts, free, classical serif) — safe,
  beautiful, but common.
- **Fraunces** (Google Fonts, variable, novel) — variable axes for
  weight + opsz + softness; characterful, modern-classical.
- **Source Serif** / **Spectral** / **Lora** — fine but generic.
- **Newsreader** (Google Fonts) — variable, gentle modern serif, good
  fragrance-magazine vibe.

Options for the body/sans slot:
- **Geist** (Vercel, free, modern but starting to be overused) — pass.
- **Public Sans** (USWDS, free, modest) — pass.
- **Inter Tight** (free) — still Inter family, flagged as default-AI.
- **Söhne / GT America** — paid, good, but can't bundle in OSS without
  license.
- **Manrope** (free, geometric, clean, less ubiquitous) — viable.
- **Switzer** (free, Indian Type Foundry, distinctive) — viable.

For monospace (technical labels — note slug, concentration, year):
- **JetBrains Mono** (free, popular but not yet flagged).
- **IBM Plex Mono** (free, good editorial mono).
- **Geist Mono** (free, matches Geist).

**Tentative recommendation: Fraunces (display) + Manrope (body) + JetBrains
Mono (technical labels), all loaded via `next/font/google` with
`display: 'swap'` and limited weights (one weight per role: Fraunces 600
display, Manrope 400/600, JetBrains 400).** The `frontend-design` skill
in design phase makes the final call. Whatever's picked, **drop Inter**.

#### U-Design-4. Theme: light + dark
shadcn defaults give us light + dark via `next-themes` (already wired in
`layout.tsx`). For an editorial palette, dark is non-trivial — naive
inversion gives "ugly dark mode."

**Tentative recommendation: ship light only in Phase 4. Add dark in a
follow-up.** The user didn't explicitly ask for dark; getting one
hand-tuned palette right is enough scope for Phase 4. The
`<ThemeProvider>` stays wired so the theme toggle can land in a later
phase without refactoring.

(Counter-argument: we already have `next-themes` configured and a
toggle widget is small. If we ship dark, it must be palette-designed,
not auto-inverted. Decision lives in design.md.)

#### U-Design-5. Imagery and the "no-bottle-image" problem
Most seed fragrances have no R2 image. We need a placeholder that:
- Looks intentional (not a broken-image icon).
- Reads at small (card grid) and large (detail hero) sizes.
- Doesn't compete with cards that DO have images.
- Encodes minimal info (initial letter? brand monogram? accord color
  swatch?).

Three options:

1. **Initial-letter monogram** on a colored panel (color from the
   accord family or from a slug-hashed palette).
2. **Pure typographic card** with no image area at all — name +
   brand in a styled type composition.
3. **Generated bottle silhouette** (CSS-only or a single SVG asset)
   styled per-card.

**Tentative recommendation: option 1 (slug-hashed colored panel + type
composition with brand name + fragrance initial).** Cheapest, scales,
and fragrances WITH images coexist cleanly because the colored panel
sits behind the image area. Implementation: a `<BottleImage>`
component that takes `imageUrl?: string`, renders `next/image` if URL
exists, otherwise the styled fallback panel.

**Open question for the user**: do we want the placeholder to be
PURELY typographic (option 2, magazine-feel) or include a colored
panel (option 1, still typographic but with surface)? Tentative: option
1 because it differentiates fragrance cards from article cards in the
same grid.

#### U-Design-6. Iconography
Today: `lucide-react` is installed (shadcn default). Per Context7, lucide
is well-maintained, tree-shakable per-icon. **Confirmed: stay on
lucide-react**. Where lucide is too generic (e.g., gender icons), we may
ship 2-3 hand-rolled SVGs (`masc`, `fem`, `unisex`, `genderfree`) — no
extra dep.

#### U-Design-7. Motion
The `frontend-design` skill recommends one well-orchestrated entrance
animation over scattered micro-interactions. Tailwind v4 has CSS
animations built-in.

**Tentative recommendation**: CSS-only animations. Specifically:
- Home: staggered reveal of hero + featured-fragrances strip on first
  paint (one cohesive motion).
- Cards: subtle hover (transform: translateY(-2px) + shadow), 150 ms.
- Page transitions: skip Framer Motion. Use Next.js's built-in
  `loading.tsx` skeleton for transitions.
- Notes pyramid: maybe a one-time fade-in on detail page mount.

No `framer-motion` / `motion` dep unless the design phase justifies it
for a specific high-impact moment. (~30 KB gzipped budget cost.)

### Risks (Design)

- **De-R1 — Generic AI slop**: the biggest single risk. Mitigation:
  invoke `frontend-design` skill at design phase, surface the chosen
  conceptual direction in design.md before any tokens land, run
  `judgment-day` adversarial review on the design doc.
- **De-R2 — Theme provider with light-only**: keeping `next-themes`
  wired but not shipping a dark palette means a half-broken toggle if
  someone toggles. **Mitigation**: do not render a theme toggle in
  Phase 4 header even though `next-themes` is wired (it stays for
  Phase 5+).
- **De-R3 — Image-less catalog**: covered above. Without an
  intentional fallback the catalog grid looks broken. Decision is the
  fallback strategy in design.md.
- **De-R4 — Font payload**: each font face is ~40-80 KB. Three families
  × 2 weights = 6 faces = ~300 KB. **Mitigation**: keep weights minimal
  (one per role), use `display: 'swap'`, audit with `next build` size
  reports.

## Sub-area 3 — Routing, navigation, and shared layout

### Unknowns

#### U-Nav-1. Header: sticky? mobile drawer?
Both are conventional; both are right for a content site.

**Tentative recommendation**:
- Sticky header on scroll (translucent / blurred backdrop after scroll
  threshold). Helps the search bar stay reachable.
- Mobile: hamburger -> shadcn `<Sheet>` drawer with the same nav links.
- Search bar visible on desktop (placeholder, disabled with a "Coming
  soon" tooltip), behind a search icon on mobile (also disabled).
- Theme toggle NOT shown in Phase 4 (light-only).

#### U-Nav-2. Breadcrumbs
Detail pages benefit from breadcrumbs (Fragrances › Chanel › Bleu de
Chanel). List pages (e.g., `/fragrances`) don't need them. Articles —
yes.

**Tentative recommendation: breadcrumbs on all detail pages and on the
articles read view.** Use shadcn's `breadcrumb` primitive (need to
install).

#### U-Nav-3. 404 / not-found
Custom `app/not-found.tsx` rendering a styled message, a search-bar
placeholder, and a "Browse fragrances" CTA. Detail-page `notFound()`
calls bubble up here.

**Tentative recommendation: yes, ship a custom not-found page.**

#### U-Nav-4. Sitemap and robots
Out of scope for Phase 4 in the brief, but cheap: `app/sitemap.ts` and
`app/robots.ts` are built-in Next.js conventions. They make the
catalog crawlable.

**Tentative recommendation: include `app/sitemap.ts` and
`app/robots.ts` in Phase 4.** Adds ~30 LOC, makes the OSS site SEO-real.
Open question for the user.

### Risks (Nav)

- **N-R1 — Sticky header on small screens**: eats vertical space.
  **Mitigation**: hide on scroll-down, show on scroll-up, or just keep
  visible — both are fine, decide in design.
- **N-R2 — Search bar that does nothing**: a placeholder input that
  takes focus then can't search is worse than no input. **Mitigation**:
  render the bar but make it non-interactive (cursor: default, disabled
  attribute) with a tooltip / inline note "Search coming soon," OR
  defer the bar entirely and add it when Phase 2 wires up. See
  Trade-off section.

## Sub-area 4 — Filter sidebar and pagination

### Unknowns

#### U-Filter-1. Filter sidebar pattern
Phase 1 spec ships filters: gender, brand (slug), perfumer (slug),
accord (repeated key, OR), concentration (slug), year_min/year_max.
Phase 4 must surface them.

Options:
1. **Sidebar always-visible on desktop, sheet on mobile.**
2. **Top-of-list horizontal filter bar + collapse-to-modal on mobile.**
3. **URL-only filters with no sidebar, just chips at top of list.**

**Tentative recommendation: option 1.** Editorial sites lean on
side-rails; an asymmetric layout (filter rail left, content right)
matches the magazine direction. shadcn `<Accordion>` for collapsible
groups, multiselect via chips. URL state via `searchParams`.

#### U-Filter-2. Pagination control
Phase 1's offset+limit envelope returns `{total, limit, offset}`.
Three viable patterns:

1. **Numbered pages** (1, 2, 3, … last). Clearest, jump-to-end works.
2. **"Load more" button**. Friendly on mobile, but hostile to RSC
   because it requires client state.
3. **Infinite scroll**. Out for an SEO-driven catalog page.

**Tentative recommendation: option 1 (numbered pages).** Fits RSC
(URL has `?offset=`), accessible, predictable. shadcn has a
`pagination` primitive (need to install).

### Risks (Filter)

- **F-R1 — URL state explosion**: 6 filter dimensions × multi-value =
  long URLs. **Mitigation**: live with it; Next.js `searchParams` typing
  handles it. Don't introduce a state library.
- **F-R2 — `loading.tsx` flicker on every filter click**: RSC re-renders
  the whole list segment. **Mitigation**: a `<Suspense>` boundary around
  the list with a skeleton, leaving filter sidebar painted; the rest of
  the page (header, sidebar) stays mounted. Standard Next.js pattern.
- **F-R3 — Filter-sidebar primitive count**: the `<Accordion>`,
  `<Sheet>` (for mobile), `<Checkbox>` or pill-button for multiselect,
  and `<Slider>` (for year range) all need to be added to
  `components/ui/`. ~5 new primitives. Manageable.

## Sub-area 5 — Beginner-friendly UX (glossary tooltips, plus the dual audience)

### Unknowns

#### U-UX-1. Glossary tooltips on jargon
Beginners encountering "drydown," "sillage," "accord," "extrait,"
"chypre" benefit from inline definitions on hover/tap. Connoisseurs
ignore them.

Options:
- **Underlined-dotted term + tooltip on hover/focus** (shadcn
  `<Tooltip>`).
- **Click-to-popover** with a longer definition.
- **Defer to a later "learn" phase** with a glossary index page.

**Tentative recommendation: implement inline tooltips on first mention
per page in Phase 4.** Cheap to ship, materially differentiates the
beginner experience, and aligns with the brief's dual-audience
requirement. Uses shadcn `<Tooltip>` (need to install). Tooltip data
lives in a static `lib/glossary.ts` map.

#### U-UX-2. Connoisseur density on detail page
Connoisseurs scan: name, brand, perfumer, year, concentration,
gender, accords, top/heart/base notes, description, articles. Detail
page must put all of those above the fold (or near it) without
feeling crowded.

**Tentative recommendation: split-hero layout** —
- Left column (~40%): bottle image / fallback panel.
- Right column (~60%): name (display serif), brand (small caps), year +
  gender + concentration in a meta strip, accords as chips, perfumer
  credit("nose:" line).
- Below the hero: notes pyramid (top → heart → base, three columns or
  one tall column on mobile), full description, articles strip,
  "more from this brand" carousel.

Final composition is a design decision. Exploration just needs to flag
that the data is dense and the layout must be deliberate.

#### U-UX-3. Markdown rendering for articles
Phase 1 articles likely store markdown. Phase 4 needs a renderer.

Options:
- **`react-markdown` + `remark-gfm`** — well-trodden, ~30 KB. Works in
  RSC.
- **`@next/mdx`** — markdown-as-component. Overkill for runtime
  content; `mdx` is for files-in-repo, not DB rows.
- **Hand-rolled marked-it** — too custom.

**Tentative recommendation: `react-markdown` + `remark-gfm`.** Sanitize
output to allowed tags. ~30 KB only on `/articles/*` pages (RSC means
we can render to HTML on the server and ship plain HTML to client —
saving the bundle hit on those pages).

### Risks (UX)

- **UX-R1 — Tooltip accessibility**: tooltips are notoriously bad on
  touch. **Mitigation**: shadcn `<Tooltip>` is Radix-based, supports
  long-press; we add an inline `(?)` icon trigger so touch users get a
  tap target. Underlined-dotted text on hover for desktop.
- **UX-R2 — Markdown XSS surface**: even server-rendered markdown can
  render unintended HTML if `react-markdown` is mis-configured.
  **Mitigation**: limit to safe tags via the `allowedElements` prop;
  no raw HTML pass-through.
- **UX-R3 — Notes pyramid layout on mobile**: three columns degrade.
  **Mitigation**: stacked single-column on `<sm`, three on `>=lg`,
  intermediate two-column at `md`.

## Sub-area 6 — Performance, accessibility, testing

### Unknowns

#### U-Perf-1. Bundle budget
shadcn primitives are tree-shaken (Radix is per-package), but Tailwind
v4 + 13 routes + lucide + `openapi-fetch` + `react-markdown` (only
on article routes via dynamic import via RSC) needs a budget.

**Tentative recommendation**:
- Initial JS budget: ≤ 180 KB gzipped on home.
- Per-route JS: ≤ 120 KB gzipped on detail pages.
- LCP target: < 2.0 s on 4G mid-tier mobile.
- CLS target: < 0.05.
- Track via `next build` size output; consider a CI check that fails on
  budget regression (deferred — Phase 5 ops).

#### U-Perf-2. Image optimization
`next/image` with `images.remotePatterns` for the R2 host. Lazy-load
below the fold (default behavior). Use `priority` only on the hero
image of detail pages.

**Tentative recommendation**: configure `remotePatterns` for the R2
public CDN host (provided by Phase 0c — open question to confirm the
hostname). Use `quality={75}` default (Next.js default), `sizes` props
for responsive bottle images.

#### U-Perf-3. Font loading
Already using `next/font` (good). Switch to the chosen font families
with limited weights and `display: 'swap'`. Subset to `latin` only
(no `latin-ext` until i18n).

#### U-Perf-4. Accessibility floor
shadcn Radix primitives are mostly WCAG-compliant by default. Phase 4
must:
- Verify color contrast (≥ 4.5:1 body, ≥ 3:1 large text) in the chosen
  palette.
- Skip-to-content link in `app/layout.tsx`.
- Logical heading order (one `<h1>` per page).
- Keyboard nav for the filter sidebar (Radix `<Accordion>` handles it).
- Visible focus rings — Tailwind v4 + Radix give them; verify with the
  custom palette.
- Alt text on every `next/image` (fragrance name + brand for bottle
  images; empty `alt=""` for decorative images).
- ARIA labels on icon-only buttons (search, theme, mobile menu).

**Tentative recommendation: ship Phase 4 to WCAG 2.1 AA. Document
exceptions (e.g., the placeholder search-bar's tooltip behavior).**

#### U-Perf-5. Testing posture
- **Unit (vitest)**: each new shared component renders without crashing
  + asserts the most distinctive prop branch. Threshold: every new
  component has at least one render test. No code-coverage target.
- **E2E (Playwright)**: smoke flows: home renders, fragrance list
  renders & paginates, fragrance detail renders, brand list renders.
  Continue the manual-trigger workflow (no Playwright on push/PR per
  the existing 0b spec).
- **Visual regression / Storybook**: deferred (Q6 in 0b confirmed
  defer). Don't add Storybook in Phase 4.
- **Lighthouse / a11y CI**: deferred to ops phase.

### Risks (Perf/A11y/Test)

- **P-R1 — Bundle creep**: each shadcn primitive is ~3-8 KB; `react-
  markdown` is ~30 KB even tree-shaken. **Mitigation**: budget
  enforcement in design.md (numeric targets), `next build` review at
  end of `sdd-apply`.
- **P-R2 — Color contrast on the warm/editorial palette**: the
  parchment/ivory + sepia direction risks low contrast on muted text.
  **Mitigation**: design phase tests every fg/bg combo against WCAG.
- **P-R3 — RSC + searchParams + Suspense pitfalls**: Next.js 16 has
  specific async/sync rules for `searchParams` (it is now async-only,
  per the 16 migration). **Mitigation**: use the documented
  `await searchParams` pattern in Next 16 RSC pages.
- **P-R4 — Test fragility on visual layouts**: snapshot tests are
  brittle. **Mitigation**: stick to behavior tests (renders, clicks
  work, link goes to the right href), no visual snapshots.

## Cross-cutting Hard Gaps (must resolve before Phase 4 design)

These are decisions that REQUIRE Phase 1's API contract to be locked
before Phase 4's `sdd-design` can finalize. **Phase 4's design should
not start until these are in `phase-1-catalog-read-endpoints/proposal.md`
or `design.md`.**

1. **OpenAPI committed file path** — Phase 1 must commit
   `apps/api/openapi.json` (per its exploration's recommendation). Phase 4
   reads from there.
2. **Pagination envelope shape** — `{data, pagination: {total, limit,
   offset}}` recommended in Phase 1 exploration. Phase 4's `<Pagination>`
   component encodes this shape; if Phase 1 picks cursor instead, Phase
   4's pagination needs a redesign.
3. **Filter parameter shape** — repeated-key OR multi-value, slug-based
   filter values, year_min / year_max range params, `?sort=field:dir`
   syntax. Phase 4's filter sidebar URL contract depends on this.
4. **Detail vs summary nesting** — list endpoints summary, detail
   endpoints nested. Phase 4's card and detail-page schemas mirror this.
5. **Error body shape** — `{"detail": "..."}` for 404. Phase 4's
   error-handling helper depends on this.
6. **Note tree shape** — `GET /notes` recursive `[{slug, name,
   children: [...]}]` is recommended in Phase 1. Phase 4's `/notes`
   page rendering depends on this.
7. **Accord ↔ fragrance linkage** — Phase 1 has a hard gap on whether
   accords link to fragrances via a join table. Phase 4 has multiple
   pages depending on accord-filtered listings: `/fragrances?accord=`
   query, `/accords/[slug]` detail. **Phase 4 design CANNOT start
   without Phase 1 picking option (a) — `fragrance_accords` join.** If
   Phase 1 picks option (c) — drop accord-filtered endpoints — Phase 4
   loses an entire route family and needs a re-scope.
8. **R2 public CDN hostname** — needed for `images.remotePatterns`.
   This is a Phase 0c / infra detail that may already be set; confirm
   in design.

## Trade-offs to flag in proposal.md

- **RSC-only vs TanStack Query**: chose RSC. Loses client-side
  optimistic UX and devtools; gains bundle weight, SEO, simplicity.
- **`openapi-fetch` (typed client) vs hand-rolled fetch**: chose typed
  client. Loses one-fewer-dep; gains discriminated `data | error`
  unions and 6 KB cost.
- **Search bar visible-but-disabled vs absent**: tentative is
  visible-but-disabled (shows the design intent). Loses "complete"
  feel; gains user expectation alignment when search ships in Phase 5+.
  **Open question for user.**
- **Light theme only vs light + dark**: chose light-only. Loses parity
  with most modern sites; gains palette quality and scope discipline.
  Dark added in a follow-up.
- **Sitemap.ts / robots.ts in Phase 4**: tentative include. Loses
  scope discipline; gains real OSS site polish for ~30 LOC.
- **Editorial direction (Fraunces + Manrope) vs minimal Swiss**:
  tentative editorial. Higher aesthetic ceiling, slightly higher
  payload cost (~+150 KB fonts), and matches the user's stated
  direction. Final call in `frontend-design`-driven design phase.
- **Glossary tooltips inline now vs deferred to a "learn" phase**:
  tentative inline now. Loses simplicity; gains beginner-audience
  satisfaction immediately.

## Cross-cutting Open Questions for the User

Before `sdd-propose`, surface explicit decisions on:

1. **Q1 — API client**: confirm `openapi-typescript` (devDep) +
   `openapi-fetch` (runtime). Tentative: yes.
2. **Q2 — Data fetching architecture**: confirm RSC-only (no TanStack
   Query in Phase 4). Tentative: yes.
3. **Q3 — Search bar visible (disabled with tooltip) or absent**?
   Tentative: visible-but-disabled.
4. **Q4 — Theme**: light-only in Phase 4, dark in a later phase?
   Tentative: yes.
5. **Q5 — Image fallback**: slug-hashed colored panel + initial-letter
   composition vs purely typographic vs CSS bottle silhouette?
   Tentative: slug-hashed colored panel.
6. **Q6 — Glossary tooltips on jargon (sillage, accord, drydown, etc.)
   inline in Phase 4** vs deferred to a later "learn" phase? Tentative:
   inline now.
7. **Q7 — Markdown library**: `react-markdown` + `remark-gfm`?
   Tentative: yes (server-render to HTML; no client JS impact).
8. **Q8 — Pagination control**: numbered pages (vs load-more vs
   infinite)? Tentative: numbered.
9. **Q9 — Sitemap and robots**: ship `app/sitemap.ts` and `app/robots.ts`
   in Phase 4? Tentative: yes.
10. **Q10 — Typography direction**: editorial (Fraunces + Manrope +
    JetBrains Mono) vs minimal Swiss (single sans family) vs
    modernist apothecary (geometric sans + low-chroma earth palette)?
    Tentative: editorial. Final call belongs to `frontend-design`
    skill in design phase, but we need user buy-in on the direction.
11. **Q11 — Split decision**: ship Phase 4 unified (all 13 routes), or
    split into 4a (spine: layout + home + fragrance list + detail) and
    4b (taxonomy + people: notes/accords/brands/perfumers/articles)?
    Tentative: SPLIT (see next section).
12. **Q12 — Storybook**: confirm still deferred. Tentative: yes (defer).
13. **Q13 — Theme toggle visible in header**: hide in Phase 4 (because
    no dark palette) or show non-functional? Tentative: hide.
14. **Q14 — Dropping Inter for the chosen body font**: confirm we
    replace `next/font/google` `Inter` import in `app/layout.tsx`.
    Tentative: yes.

## Recommendation: Split Phase 4 in two

**Tentative recommendation: SPLIT**, with caveats.

**Phase 4a — "the spine"**:
- Site-wide layout: `<SiteHeader>`, `<SiteFooter>`, navigation,
  responsive shell, theming setup, fonts swap, palette tokens, skip-to-
  content, image-fallback `<BottleImage>` component.
- Home (`/`): hero, featured fragrances, accord teaser, note teaser,
  recent articles teaser strip, footer.
- `/fragrances` (list with filter sidebar + pagination).
- `/fragrances/[slug]` (detail).
- `app/not-found.tsx`, `app/error.tsx`, `app/global-error.tsx`,
  `app/sitemap.ts`, `app/robots.ts` (if Q9 yes).
- API client setup (`openapi-typescript` + `openapi-fetch`),
  `images.remotePatterns`, `next.config.ts` updates.
- Glossary tooltip mechanism (used on detail page jargon).

**Phase 4b — "supporting taxonomy and people"**:
- `/notes` + `/notes/[slug]`.
- `/accords` + `/accords/[slug]`.
- `/brands` + `/brands/[slug]`.
- `/perfumers` + `/perfumers/[slug]`.
- `/articles` + `/articles/[slug]` (markdown rendering setup).

**Why split**:
- 4a defines the design system, layout shell, image fallback strategy,
  API client, and the most complex page (detail). Once those land,
  4b is mechanical: copy a list-detail pattern × 4 taxonomy/people
  resources + the markdown renderer for articles.
- 4a is the highest-risk slice (palette, typography, fragrance card,
  pagination contract) and should land standalone for review (e.g.,
  `judgment-day` on the design before 4b commits to those tokens).
- 4b's pages are smaller (no filter sidebar, no notes-pyramid
  complexity), so review fatigue is lower.
- 13 routes + design system + filter sidebar + glossary + markdown +
  4 new shadcn primitives in a single change exceeds the "complete in
  one session" guidance for tasks. Splitting halves each `sdd-apply`
  pass.

**Why NOT split (counter-argument)**:
- The catalog is incomplete without taxonomy pages — clicking an
  accord chip in 4a should go somewhere. Mitigation: 4a links to
  `/accords/[slug]` but those pages 404 until 4b lands; or 4a
  renders the chips as non-links until 4b. The latter feels
  half-finished and reads as "broken" to a reviewer.

**Resolution proposal**: Split, but keep 4a and 4b sequential and
back-to-back. 4a's accord/note/brand/perfumer chips render as
non-interactive (or fall back to the `/fragrances?accord=...` filtered
list, which exists in 4a) until 4b ships them as clickable detail
pages. This is honest scoping; the user sees one phase land
fully-functional, then the next.

If the user prefers unified: keep all 13 routes in one change but
plan `sdd-apply` to run in batches (layout+home → list+detail → notes
→ accords → brands → perfumers → articles), which is effectively a
split inside one change folder.

## Risks (consolidated)

- **R1 — API contract drift (hard gap)**: see Hard Gaps #1-#7. Phase 4
  design must wait for Phase 1 design.
- **R2 — Generic AI design slop**: covered in U-Design-1. Mitigated by
  invoking `frontend-design` and `judgment-day`.
- **R3 — Image-less catalog looking broken**: covered in U-Design-5.
  Mitigated by intentional fallback design.
- **R4 — Bundle bloat**: covered in U-Perf-1. Mitigated by numeric
  budget.
- **R5 — Accord linkage missing in API (hard gap)**: see Hard Gap #7.
  Phase 4 has 3+ routes depending on accord-filtered listings; if
  Phase 1 doesn't ship the join table, Phase 4 loses route surface.
- **R6 — RSC + filter sidebar perceived latency**: covered in D-R3.
  Mitigated by Suspense + skeletons.
- **R7 — Search bar UX mismatch**: covered in N-R2. Decision in Q3.
- **R8 — Light-only theme regression risk**: covered in De-R2. Hide
  the toggle in 4; add palette + toggle later.
- **R9 — Glossary tooltip touch UX**: covered in UX-R1.
- **R10 — `next-themes` and SSR class flash**: already handled in 0b
  via `suppressHydrationWarning` on `<html>`. No new risk.

## Ready for Proposal

**Partial.** The orchestrator should report back to the user with:
- The 14 cross-cutting questions (Q1–Q14) above. Most have tentative
  recommendations and the user can ratify in bulk.
- The 7 hard gaps that REQUIRE Phase 1 contract to be locked first.
  Phase 4 `sdd-design` should not start until Phase 1's
  `proposal.md`/`design.md` answers them.
- The split recommendation (4a + 4b sequential) — needs explicit user
  call before `sdd-propose`.

Once those decisions are in (especially Q11 split, Q3 search bar, Q10
typography, plus all 7 Phase 1 hard gaps),
`sdd-propose` for `phase-4a-...` (or unified `phase-4-...`) can run
with high confidence. The `frontend-design` skill should be invoked
during `sdd-design`, not exploration.

---

## Return Envelope

**Status**: success
**Summary**: Exploration of phase-4-web-home-and-catalog-ui complete.
Surfaced 14 cross-cutting open questions and 7 hard gaps that lock
Phase 4 design to Phase 1's API contract. Verified library state via
Context7 for Next.js 16.2.2 fetch caching / `images.remotePatterns`,
`openapi-typescript` + `openapi-fetch` (the 6 KB typed client passes
Next.js `next: { revalidate, tags }` through), and TanStack Query v5
options (recommended skip in Phase 4). Identified the largest single
risk as "generic AI design slop"; recommended invoking the
`frontend-design` skill during `sdd-design`. Recommended SPLIT into
4a (spine: layout + home + fragrance list + detail + design system +
API client) and 4b (taxonomy + people: notes / accords / brands /
perfumers / articles). Tentative aesthetic direction: editorial
perfumery (Fraunces display + Manrope body + JetBrains Mono
technical), light-only theme, slug-hashed colored panel as image
fallback, RSC-only data fetching with ISR, numbered pagination,
visible-but-disabled search placeholder, glossary tooltips on first
mention, sitemap + robots in Phase 4.
**Artifacts**:
`openspec/changes/phase-4-web-home-and-catalog-ui/exploration.md`
**Next**: User decisions on Q1-Q14 (especially Q11 split decision)
AND completion of Phase 1's `proposal.md`/`design.md` covering the 7
hard gaps. Then `sdd-propose` for `phase-4a-web-spine` (or unified
`phase-4-...` if user vetoes split).
**Risks**: 10 risks itemized (R1 API contract drift, R2 AI design
slop, R3 image-less catalog, R4 bundle bloat, R5 accord linkage gap,
R6 RSC filter latency, R7 search bar UX, R8 light-only theme, R9
tooltip touch UX, R10 SSR class flash already handled). The two
material ones blocking `sdd-design` are **R1** and **R5** — both
inherited from Phase 1.
**Skill Resolution**: fallback-path — loaded
`~/.claude/skills/sdd-explore/SKILL.md` plus `_shared/sdd-phase-common.md`
and `_shared/openspec-convention.md`. The `frontend-design` skill was
located but NOT invoked (per skill instructions, exploration only
surveys; design phase invokes). Project-standards block was not
pre-injected.
