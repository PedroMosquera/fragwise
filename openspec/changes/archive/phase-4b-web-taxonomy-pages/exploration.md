# Exploration: Phase 4b — Web Taxonomy Pages

> **Status**: exploration only. No code, no design decisions ratified.
> Surfaces unknowns, risks, and trade-offs. The orchestrator returns
> with a list of decisions the user MUST ratify before `sdd-propose`.

## Current State (post-4a)

`apps/web/` is a working Next.js 16.x App Router app with the
"editorial perfumery" design language locked by Phase 4a (ADR-0033).
Three pages live and reachable:

- `/` — hero + 6 mood tiles + featured strip + journal placeholder
- `/fragrances` — filterable, paginated grid (URL-driven)
- `/fragrances/[slug]` — split hero + Pyramid + description + articles

Header NAV currently renders **Notes / Accords / Brands / Perfumers /
Journal** as `<span aria-disabled="true" title="Coming with phase 4b">`
placeholder labels (see `apps/web/components/site/Header.tsx:33-44`).
The mood tile grid on home links to `/fragrances?accord=<slug>` (4a
fallback) rather than `/accords/<slug>` (which doesn't exist yet).

Reusable assets shipped by 4a that 4b SHOULD lean on:

- `components/catalog/FragranceCard.tsx` + `FragranceCardSkeleton.tsx`
- `components/catalog/Pagination.tsx` (URL `?offset=` driven, boundary disable)
- `components/catalog/ImageFallback.tsx` (SHA-256 deterministic panel)
- `components/catalog/AccordBadge.tsx` + `NoteBadge.tsx`
- `components/catalog/FilterSidebar.tsx` (composable; can be omitted for taxonomy detail pages)
- `components/site/Glossary.tsx` (Radix Popover wrapper, F8/F10 settled)
- `components/site/Container.tsx` (page width container)
- `lib/api/fetchers.ts` (typed openapi-fetch helpers; canonicalize array params; `getAllAccords`, `getAllBrands` already exist)
- `lib/api/types.ts` (regenerated from `apps/api/openapi.json`)
- `lib/glossary.ts` (12 seed terms)

shadcn primitives already installed: `accordion`, `breadcrumb`,
`pagination`, `popover`, `command`, `scroll-area`, `select`, `sheet`,
`skeleton`, `tooltip`, plus the 10 from 0b. **No new shadcn add is
required for 4b** unless we adopt a tree component (see Q3).

Tokens are light-only (`apps/web/styles/tokens.css:7-41`); no
`.dark { ... }` selector exists. `theme-provider.tsx` is a thin wrapper
over `next-themes`'s `ThemeProvider`. ADR-0037 deferred dark to 4b.

`apps/web/app/sitemap.ts` only enumerates `/`, `/fragrances`, and
fragrance slugs. No brand / perfumer / article / accord / note slugs.

## OpenAPI Contract Reality (CRITICAL)

**The OpenAPI committed to `apps/api/openapi.json` is leaner than what
4b's nominal scope suggests.** Schemas inspected:

| Resource | Detail schema fields |
|---|---|
| `NoteDetail` | `slug`, `name`, `parent: NoteSummary \| null`, `fragrances: ListEnvelope[FragranceListItem]` |
| `AccordDetail` | `slug`, `name`, `fragrances` |
| `BrandDetail` | `slug`, `name`, `fragrances` |
| `PerfumerDetail` | `slug`, `name`, `fragrances` |
| `ArticleDetail` | `slug`, `title`, `body: string \| null`, `published_at: datetime \| null`, `fragrances: FragranceListItem[]` |

There is **no `bio`** on `PerfumerDetail`, **no `description` /
`founded` / `country` on `BrandDetail`**, **no `topics` / `tags` on
`ArticleDetail`**, **no `description` / `parent_chain` /
`children` on `NoteDetail`**, **no curated copy on `AccordDetail`**.

`GET /api/v1/notes` returns `NoteTreeEnvelope` (data: `NoteTreeNode[]`)
where each `NoteTreeNode = { slug, name, children: NoteTreeNode[] }`.
That is the FULL recursive tree (no pagination).

`GET /api/v1/brands?q=` and `GET /api/v1/perfumers?q=` accept a `q`
substring filter (max 100 chars). `q` is NOT an offered query param
on `/notes`, `/accords`, or `/articles`.

This significantly de-risks design (no biography typography to spec,
no rich brand/article header to design) but also means 4b detail pages
are deliberately spare. A future phase will enrich the schemas.

## Affected Areas (file map)

### New routes (10)

- `apps/web/app/(site)/notes/page.tsx` — tree
- `apps/web/app/(site)/notes/[slug]/page.tsx`
- `apps/web/app/(site)/notes/[slug]/loading.tsx`
- `apps/web/app/(site)/accords/page.tsx`
- `apps/web/app/(site)/accords/[slug]/page.tsx`
- `apps/web/app/(site)/accords/[slug]/loading.tsx`
- `apps/web/app/(site)/brands/page.tsx`
- `apps/web/app/(site)/brands/[slug]/page.tsx`
- `apps/web/app/(site)/brands/[slug]/loading.tsx`
- `apps/web/app/(site)/perfumers/page.tsx`
- `apps/web/app/(site)/perfumers/[slug]/page.tsx`
- `apps/web/app/(site)/perfumers/[slug]/loading.tsx`
- `apps/web/app/(site)/articles/page.tsx`
- `apps/web/app/(site)/articles/[slug]/page.tsx`
- `apps/web/app/(site)/articles/[slug]/loading.tsx`

Some `loading.tsx` files may be omitted if a page has no Suspense
boundary distinct from the layout's. Decide in design.

### Touched files

- `apps/web/components/site/Header.tsx` — promote 5 NAV placeholders
  to active `<Link>` (or 1-by-1, see Q9).
- `apps/web/app/(site)/page.tsx` — change `MOODS` hrefs from
  `/fragrances?accord=<slug>` to `/accords/<slug>` (or keep, see Q10).
- `apps/web/app/sitemap.ts` — append brand/perfumer/article/accord/note
  slug enumeration (using the same `MAX_PAGES` cap pattern).
- `apps/web/lib/api/fetchers.ts` — add 10 new fetchers (`getAllNotesTree`,
  `getNoteBySlug`, `getAllAccordsList` already exists, `getAccordBySlug`,
  `getBrands` (paginated + q), `getBrandBySlug`, `getPerfumers`,
  `getPerfumerBySlug`, `getArticles`, `getArticleBySlug`).
- `apps/web/lib/api/types.ts` — regenerated; should be a no-op if
  openapi.json hasn't drifted, but 4a `predev`/`prebuild` hook will
  regenerate.

### New components (estimate)

- `components/catalog/NoteTree.tsx` — recursive tree-view (likely
  shadcn `Accordion` wrapping itself, or a custom flat indented list
  with disclosure triangles; see Q3).
- `components/catalog/BrandCard.tsx` — small list card
- `components/catalog/PerfumerCard.tsx` — small list card; portrait
  fallback if/when API gains an avatar
- `components/catalog/AccordCard.tsx` — list grid tile (visual color
  swatch + name)
- `components/catalog/ArticleCard.tsx` — title + published-at +
  optional excerpt slot (no excerpt field today, see Q5)
- `components/catalog/ArticleBody.tsx` — markdown renderer (server
  component if `react-markdown` v9 still works in RSC; verify in design)
- `components/site/SearchInput.tsx` — debounced URL `?q=` input
  (client component) for brand/perfumer list pages
- (Conditional, see Q11) `components/site/ThemeToggle.tsx` —
  `useTheme().setTheme(...)` button

### Optional asset additions

- A dark token block in `tokens.css` if the dark theme ships in 4b.
- Possibly `lib/api/fetchers-tax.ts` if `fetchers.ts` exceeds ~400 LOC.

## Approaches & Open Questions

### Q1 — Articles body format: markdown vs HTML vs plaintext

`ArticleDetail.body` is `string | null`. The OpenAPI says nothing about
its format. Possibilities:

- **A**: Treat as **GFM markdown**, render with `react-markdown` +
  `remark-gfm` + `rehype-sanitize`. Accepts headings, lists, tables,
  links. Sanitization layer catches inline `<script>` if a content
  pipeline ever leaks raw HTML.
- **B**: Treat as **plain text**, render in a `<p>` with `whitespace:
  pre-wrap`. Simplest; assumes editorial pipeline produces no
  formatting.
- **C**: Treat as **trusted HTML** with `dangerouslySetInnerHTML`.
  Fastest but trusts whoever populates the field.

The original `phase-0c-schema-and-ontology` exploration (search
the archive — outside this scope) almost certainly assumed markdown
because that's the editorial convention; OSS perfumery articles are
rarely written in HTML. **Confirm with the user** which the seed
ingestion pipeline produces. If unknown, **A is the safe default**:
markdown plus `rehype-sanitize` will render plain text faithfully
(no markdown-special characters except `*` and `_`) AND format
markdown if present. This is the recommended path.

Bundle-cost note: `react-markdown@9` + `remark-gfm@4` +
`rehype-sanitize@6` is ~25-32 KB gzipped (Context7 verified the
package is ESM-only and supports server-component rendering). Only
loaded on `/articles/[slug]` — should fit under the size-limit budget
because article pages aren't critical-path (home and list are).

### Q2 — Sanitization posture: schema or scrub?

Within Approach A above, two sub-choices for `rehype-sanitize`:

- **A1**: Pass it the default `defaultSchema` (allowlists
  link, image, list, blockquote, code, headings, etc.).
- **A2**: Pass it a custom schema dropping `img` (no images in
  articles seeded yet) and `iframe` etc.

Recommend **A1** for 4b — ship safe defaults, tighten if the seed
content ever produces something unexpected.

### Q3 — Note tree visualization

`NoteTreeEnvelope.data` is fully recursive; depth is bounded by P1's
selectinload depth-10 guard. We render the entire tree. Options:

- **T1 — Nested shadcn `Accordion`**: each branch is an
  AccordionItem. Children are recursively rendered via a `NoteTree`
  component. Pros: shadcn primitive already installed, native
  keyboard support. Cons: large trees expand to a long DOM; nested
  accordions can confuse screen readers if not labelled correctly.
- **T2 — Indented disclosure list (custom)**: a `<ul>` with
  click-to-toggle `<button>` disclosures and indented children.
  Pros: lightest DOM; full control over a11y semantics. Cons: more
  code; we recreate something `Accordion` already does.
- **T3 — Two-pane layout (NotePicker + NoteDetail inline)**: left
  rail is the tree, right pane shows fragrances when clicked.
  Pros: powerful UX. Cons: requires `/notes/[slug]` data fetched
  client-side or `?selected=` URL param; far more complex than the
  rest of 4b.

Recommend **T1** (nested `Accordion`) and ALL top-level branches
collapsed by default. If seed taxonomy has hundreds of leaf notes
across ~7 top-level families (woody, floral, fresh, oriental, gourmand,
spicy, aromatic), this stays manageable. Open question: collapse all
or expand top-level for first paint? Suggest collapse-all to keep
above-the-fold tight.

### Q4 — Notes list page: pagination?

`GET /api/v1/notes` is **not paginated** — it returns the whole tree.
There's no `?limit` or `?offset`. So the question becomes: does the
frontend impose any visual pagination? If the tree is 200+ leaves,
DOM weight matters but is acceptable for an SSR'd accordion that
defaults to collapsed.

Recommend **no client-side pagination on `/notes`**. Render the full
tree, all top-level branches collapsed, leaf count shown in the
branch header (e.g., "Floral · 47 notes").

### Q5 — Article excerpt / hero snippet

`ArticleSummary` has only `slug`, `title`, `published_at`. No excerpt,
no hero image, no topics. The article list card therefore displays
title + relative time + a `→` affordance. No risk of a "snippet
component" yet.

Recommend a deliberately editorial card: large Fraunces title, tiny
mono-font date, hairline rule between cards; no images; centred
within a constrained body width (~64ch).

### Q6 — Brand/perfumer detail: full FragranceCard grid or compact list?

Both "Detail" responses bundle a `ListEnvelope[FragranceListItem]`
with the same shape as `/fragrances`. We could:

- **D1**: Reuse the same `FragranceCard` grid as `/fragrances`,
  no FilterSidebar, just `Pagination`. Cons: visually identical to
  `/fragrances` filtered by brand — possibly redundant.
- **D2**: Compact list (1-line per fragrance: name · year ·
  concentration · `→`). Cons: visually distinct but loses the
  bottle/fallback panel which is where 4a's editorial flavor lives.
- **D3**: Hybrid — first 6 as cards, rest as list ("show all").
  Cons: more components to test.

Recommend **D1**. Brand/perfumer pages ARE shaped like the filtered
list (because semantically that's what they are); the difference is
the page header's editorial framing (brand name in Fraunces, perfumer
attribution, accord summary) which gives them voice. Identity is
hierarchy + framing, not a different card.

### Q7 — Accord detail page: filtered list shortcut or curated voice?

Same dilemma. `AccordDetail.fragrances` is "all fragrances tagged with
this accord" — semantically equivalent to `/fragrances?accord=<slug>`.

- **A1**: 4b's `/accords/<slug>` redirects to `/fragrances?accord=<slug>`
  (i.e. accord pages don't exist as standalone pages).
- **A2**: 4b's `/accords/<slug>` renders its own page with a hero
  block ("Woody — earthy, smoke, resin" — copy hardcoded in a small
  `lib/accord-copy.ts` map) and the same filtered grid below.
- **A3**: Same as A2 but the "voice" copy comes from the API once
  schemas grow a `description` field (P5+).

Recommend **A2**. A short curated description is editorial and lives
in the frontend until schema enrichment lands. ~6 accord families
× ~80 chars of copy = trivial to maintain in the repo. This also
preserves a stable URL for mood tiles to point at.

### Q8 — Mood tile hrefs

Two options:

- **M1**: Promote mood tile hrefs from `/fragrances?accord=<slug>`
  (4a fallback) to `/accords/<slug>`.
- **M2**: Keep `/fragrances?accord=<slug>` (matches "browse by mood
  ⇒ filtered list" mental model).
- **M3**: Render two affordances on each tile: tile-body links to
  `/accords/<slug>` (curated page), small "View all →" sublink goes
  to `/fragrances?accord=<slug>` (raw filtered list).

If we take **A2** for accord detail (curated voice), then **M1** is
the natural pairing: the tile teases the accord, the page gives the
voice. Recommend **M1** (single href to `/accords/<slug>`).

### Q9 — Header NAV promotion: atomic or rolling?

5 placeholder spans currently. Options:

- **N1 — Atomic**: in the same task that lands the LAST 4b page,
  drop all 5 placeholders to active `<Link>`. Risk: any partial-deploy
  state shows broken links.
- **N2 — Rolling**: as each route ships, that NAV item flips to a
  Link. Pro: each commit is independently shippable. Con: 5 separate
  edits to `Header.tsx` adds noise to PR reviews.
- **N3 — Feature flag map**: a single `lib/site-nav.ts` module
  exports `{ slug: { href, ready: boolean } }`. Header reads from
  it. Routes flip `ready: true` as they land.

Recommend **N3** — adds 6 lines of code and makes the rollout
trivially auditable. Only one edit per route to `lib/site-nav.ts`.

### Q10 — Dark theme: ship in 4b or split to 4c?

Pulled from ADR-0037 ("light-only in 4a; revisit in 4b"). Considerations:

- Token additions needed: full duplicate `.dark { ... }` block in
  tokens.css with WCAG AA contrast for every color pair. Editorial
  perfumery aesthetic is harder in dark — sepia/ivory must translate
  to a paper-on-charcoal mood, not a generic "dark mode" inversion.
  The `frontend-design` skill should re-engage to locate the dark
  palette.
- Provider edit: `app/layout.tsx` currently passes
  `forcedTheme="light"`; flip to `enableSystem` (Context7 verified
  this is the documented pattern).
- Toggle UI: shadcn `dropdown-menu` with three items (Light / Dark /
  System), placed in `Header.tsx`. ~30 LOC plus `lucide-react`'s
  `SunMedium` / `Moon` / `Monitor` icons.
- Tests: vitest render under both themes; Playwright smoke per theme.

Bundle cost: minimal (`next-themes` already a dep; tokens.css is
build-time CSS; the toggle adds a few KB of JS for the dropdown-menu
which is already loaded elsewhere).

**The real cost is design, not engineering**: getting the dark palette
right is half a `frontend-design` invocation plus `judgment-day`. If
4b is already 10 pages + a markdown renderer, dark adds noticeable
review burden.

Three resolutions:

- **K1 — Ship dark in 4b**: one big phase, one design pass. Pros:
  the toggle that already scaffolds in `theme-provider.tsx` becomes
  meaningful immediately. Cons: review fatigue.
- **K2 — Split dark into 4c**: 4b is taxonomy ONLY; 4c is dark
  theme + any remaining QoL. Pros: smaller cognitive load per
  phase. Cons: another hop before the site feels "complete".
- **K3 — Ship a dark TOKEN block in 4b but no toggle**: i.e. write
  the `.dark { ... }` rules in tokens.css and the `prefers-color-scheme`
  media query, but don't expose a toggle. Pro: respects OS preference
  for free. Con: users can't override, and we still need the design
  pass for the dark palette.

Recommend **K2 — split dark into 4c**. 4b is already 10 pages +
markdown + sitemap diff + nav promotion + 6 new components; adding a
designed-from-scratch dark palette roughly doubles the design surface.

### Q11 — Search bar: Header or per-page?

The Header search input shipped in 4a is **disabled** with placeholder
text "Search coming soon". Two scopes:

- **S1 — Per-page `?q=` inputs only on `/brands` and `/perfumers`**
  (the only resources where the API supports `q`). Header search
  stays disabled. Search across the whole catalog is `phase-2-hybrid-search`
  territory and IS shipped in P2; whether 4b lights it up in the
  Header is a separate decision.
- **S2 — Promote the Header search to typeahead** — Phase 2's
  `/api/v1/search` endpoint exists. Could be a new shadcn `Command`
  palette (already installed) with debounced async items.
- **S3 — Both** — per-page `?q=` for brand/perfumer lists AND
  Header typeahead.

**Recommend S1.** Header search promotion is meaty enough to be its
own phase ("phase-4c-header-search" or "phase-5-search-ui"). 4b's job
is to make the brand/perfumer LIST pages searchable via URL `?q=`,
which is a 30-line `SearchInput` client component plus a fetcher
extension. Be explicit in the proposal that Header search remains
disabled in 4b.

### Q12 — Brand/perfumer search input UX: debounced URL or live typeahead?

If we accept **S1**, two implementations:

- **U1 — Debounced URL**: input on the page, debounced
  (`useDebouncedCallback` ~300ms), updates URL `?q=`, server re-renders
  with the filtered list. Pure RSC + `<Link>` semantics; no client-side
  cache. Honest about latency.
- **U2 — Client typeahead**: input on the page, client fetches
  results into a `Command` popover, navigation when an item is
  picked. UX is snappier but writes a chunk of state we don't need.

Recommend **U1** — matches 4a's URL-state principle. The list is
small (likely <500 brands, <2000 perfumers) so server roundtrip is
fast.

### Q13 — Per-page ISR `revalidate` values

All pages should pass `next: { revalidate, tags }` per ADR-0035. Suggested:

| Surface | revalidate | tags |
|---|---|---|
| `/notes` (tree) | 3600 (rare changes) | `notes:tree` |
| `/notes/[slug]` | 600 | `note:<slug>` |
| `/accords` | 3600 | `accords:list` |
| `/accords/[slug]` | 600 | `accord:<slug>` |
| `/brands` | 3600 (or 600 if `q`) | `brands:list` |
| `/brands/[slug]` | 3600 | `brand:<slug>` |
| `/perfumers` | 3600 (or 600 if `q`) | `perfumers:list` |
| `/perfumers/[slug]` | 3600 | `perfumer:<slug>` |
| `/articles` | 600 (editorial) | `articles:list` |
| `/articles/[slug]` | 600 | `article:<slug>` |

Open question: list pages with a `?q=` searchParam — does the same
revalidate window apply when the cache key includes the canonicalized
`q`? Yes, but with `q` set the cache hit rate drops to ~0 (each user
types something different), so the revalidate is effectively
per-request. Acceptable.

### Q14 — Sitemap impact

The sitemap loop in `app/sitemap.ts` already has a `MAX_PAGES = 200`
guard. We replicate the same pattern for brands/perfumers/articles.
For `/notes` the tree is non-paginated, so we walk the tree once and
emit each leaf + each branch.

Open question: do we WANT to emit every note slug in the sitemap?
Notes are leaf taxonomy and may number in the hundreds; emitting all
of them inflates sitemap.xml size. Recommend yes — they're stable
URLs that rank for long-tail queries. The MAX_PAGES guard already
caps catastrophic blowup.

### Q15 — Glossary across new pages

Long-form copy on accord detail pages (curated voice, see Q7) and
article body content should both wrap recognized jargon in
`<Glossary>`. For accord copy this is straightforward (we author
the copy). For article markdown, automatic glossary wrapping is
NOT proposed in 4b — too invasive a markdown-AST transform for the
schedule, and risks double-wrapping if an author references "sillage"
plain or "[sillage](/glossary/sillage)" (which doesn't exist yet).

Recommend: **manual `<Glossary>` only on hand-authored frontend copy
in 4b** (specifically the accord detail blurbs). Articles render
markdown as-is; a future phase can ship a `remark-glossary` plugin.

### Q16 — Per-resource detail page `<head>` metadata

`generateMetadata` should be implemented per detail page (open graph
title = resource name + " — Fragwise"; description fallback to page
heading). Especially important for articles which want share-friendly
titles.

Recommend: ship `generateMetadata` for every `[slug]` page in 4b.
~10 LOC each.

## Reused vs New Components

### Reused (no change required)

- `FragranceCard`, `FragranceCardSkeleton`
- `Pagination` — for accord/brand/perfumer/article list pages
- `ImageFallback` — used by FragranceCard internally
- `Glossary` — used in hand-authored accord blurbs
- `AccordBadge`, `NoteBadge`
- `Container`, `Header`, `Footer`, `MobileMenu`, `SkipToContent`

### New (5-7 components)

- `NoteTree` (recursive, see Q3)
- `BrandCard`, `PerfumerCard`, `AccordCard`, `ArticleCard`
- `ArticleBody` (markdown renderer, RSC)
- `SearchInput` (debounced URL `?q=`)

## Approaches Comparison: Phase Splitting

| Split | Phases | Pros | Cons | Effort |
|---|---|---|---|---|
| **U** unified | 4b: all 10 pages + dark | 1 design pass, 1 review pass | Largest single review surface (~30 component edits) | High |
| **U-no-dark** | 4b: 10 pages, 4c: dark | Manageable taxonomy phase; dark gets dedicated `frontend-design` time | Two phases | Medium |
| **2-axis** | 4b-1: notes+accords (taxonomy); 4b-2: brands+perfumers (people); 4b-3: articles+dark | Each phase ~3 pages; smallest reviews | Three sequential phases ⇒ 3 propose/spec/design cycles | Low per phase, high overall |
| **3-axis** | 4b-1: taxonomy; 4b-2: people; 4b-3: articles; 4c: dark | Cleanest separation | 4 phases ⇒ longest cycle | Same |

**Recommend U-no-dark** (current scope minus dark): keep the 10 pages
in one phase because they share the list-detail pattern + sitemap
edit + Header NAV promotion + new fetcher block. Splitting them
creates 3 redundant rounds of "regenerate types, edit fetchers, edit
sitemap, edit NAV map". Defer dark to its own phase 4c with a
dedicated `frontend-design` invocation for the dark palette.

## Risks (consolidated)

- **R1 — Markdown bundle bloat**: ~30 KB on `/articles/[slug]`. Goal
  is to keep total page size under whatever 4a's `.size-limit.json`
  budgets per route. **Mitigation**: dynamic import the renderer if
  it pushes past the budget; or load only `react-markdown` core
  (skip GFM) if articles don't use tables/strikethrough. Verify
  empirically in design.
- **R2 — Missing schema fields surface "thin" pages**: Brand and
  perfumer detail pages have only name + fragrance list. Without
  some editorial framing they will look like `/fragrances?brand=X`.
  **Mitigation**: design pass deliberately makes the page header
  hierarchical (Fraunces 5xl-7xl name; mono-font credit line; an
  optional 1-line tagline copy that's hand-authored per brand for
  the top 10 brands). Same for perfumers.
- **R3 — Note tree DOM weight**: 200+ leaves in nested accordions.
  **Mitigation**: SSR expanded for the SEO crawl, `defaultValue=[]`
  so all branches collapsed for first paint. Each accordion opens
  client-side without re-render.
- **R4 — Dark theme contrast drift**: if K1 (ship dark in 4b) is
  taken, every token pair must hit WCAG AA in dark. **Mitigation**:
  `frontend-design` reinvocation; `judgment-day` review; manual
  contrast audit. R4 disappears under K2 (defer dark).
- **R5 — Article body XSS**: if backend ever leaks user-generated
  content into `body`. **Mitigation**: `rehype-sanitize` baseline.
- **R6 — Header NAV partial-deploy state**: routes activate before
  every page is wired. **Mitigation**: Q9 N3 (feature flag map)
  prevents this entirely.
- **R7 — Sitemap blowup**: brands × perfumers × articles × notes ×
  accords = potentially 1000+ entries. **Mitigation**: MAX_PAGES
  cap already in 4a's pattern; trust the cap.
- **R8 — Type-gen drift**: regenerated `types.ts` may differ from
  committed file if ingestion changes the schema. The 4a CI gate
  already catches this. **Mitigation**: none new; existing gate.
- **R9 — Accord/note empty states**: an accord with zero fragrances
  or a note that maps to nothing in seed. **Mitigation**: empty-state
  treatment (1 line of copy + link back to `/fragrances`). Already
  the pattern from 4a's filter empty state.
- **R10 — Spec word budget**: 10 new pages × 2-3 reqs each + 5-7
  new components × 1-2 reqs = 30-50 new requirements in the
  `fragrance-catalog-ui` and `web-app` deltas. The spec phase
  should plan for an "added/modified/breakdown" section near the
  top so the orchestrator can route review.
- **R11 — `react-markdown` ESM-only**: confirmed by Context7. Next.js
  16 supports ESM-only deps in App Router; the existing 4a `next.config.ts`
  may need `transpilePackages: ['react-markdown', 'remark-gfm', 'rehype-sanitize']`.
  Verify in design.
- **R12 — `notFound()` on detail pages**: each `[slug]` page must
  call `notFound()` on 404. The `getXBySlug` pattern in 4a's
  `fetchers.ts` does this for fragrance; replicate.

## Trade-offs (concise)

| Trade-off | Lean toward |
|---|---|
| Markdown library | `react-markdown@9` + `remark-gfm@4` + `rehype-sanitize@6` |
| Note tree | shadcn `Accordion` recursive, all collapsed |
| Notes pagination | None — render whole tree |
| Brand/perfumer detail layout | Same FragranceCard grid + page header |
| Accord detail | Curated 1-paragraph blurb in `lib/accord-copy.ts` + grid |
| Mood tile target | `/accords/<slug>` (M1) |
| Header NAV promotion | Feature-flag map (N3) |
| Brand/perfumer search | Debounced URL `?q=` (U1) |
| Header search | Stay disabled (S1) |
| Dark theme | Defer to 4c (K2) |
| Article markdown sanitization | Default `rehype-sanitize` schema |
| Glossary in articles | No (manual on accord blurbs only) |
| Sitemap inclusion | All 5 new resource types |
| Per-page metadata | Yes (`generateMetadata`) |

## Decisions the User Must Ratify Before `sdd-propose`

The orchestrator should report back with these and request
yes/no/alt:

1. **D-Markdown**: Adopt `react-markdown@9` + `remark-gfm@4` +
   `rehype-sanitize@6` for `/articles/[slug]`. (Q1, Q2)
2. **D-NoteTree**: Implement note tree as recursive shadcn
   `Accordion`, all top-level branches collapsed by default. (Q3)
3. **D-NotesPagination**: No client-side pagination on `/notes`. (Q4)
4. **D-DetailLayout**: Brand and perfumer detail pages reuse
   `FragranceCard` grid + `Pagination` under an editorial page header.
   No "compact list" alternate. (Q6)
5. **D-AccordDetail**: Accord detail pages are standalone (NOT
   redirects), with hand-authored 1-paragraph blurbs from
   `lib/accord-copy.ts`. (Q7)
6. **D-MoodTiles**: Promote home page mood tile hrefs from
   `/fragrances?accord=<slug>` (4a fallback) to `/accords/<slug>`. (Q8)
7. **D-NavPromotion**: Use a `lib/site-nav.ts` feature-flag map;
   each route flips its `ready` flag as it lands. (Q9)
8. **D-DarkTheme**: **Defer dark to phase 4c.** 4b is light-only +
   10 pages. (Q10)
9. **D-HeaderSearch**: Header search stays disabled in 4b. (Q11)
10. **D-PerPageSearch**: Brand and perfumer list pages get a debounced
    URL `?q=` input only. (Q11, Q12)
11. **D-Sitemap**: Include all 5 new resource types in `sitemap.ts`. (Q14)
12. **D-Glossary**: Glossary popovers only on hand-authored accord
    blurbs in 4b; articles render raw markdown. (Q15)
13. **D-Metadata**: `generateMetadata` on every detail page in 4b. (Q16)
14. **D-Phase4aFollow-ups**: Drop F12 from the 4a follow-ups list now
    that 4b is locking the spec wording ("links MUST resolve to 200
    via 4b routes"). Confirm none of F1-F13 contradict 4b plans
    (none do, on inspection).

If the user wants to alter any of these (e.g. ship dark in 4b,
adopt MDX instead of markdown, render a compact list on brand
pages), the orchestrator should record the decision and pass it
to `sdd-propose`.

## Recommendation

**Ship 4b unified for the 10 pages, defer dark theme to 4c.**

Rationale: the 10 pages share enough infrastructure (fetchers, Header
NAV map, sitemap, generated types) that splitting them re-pays the
same setup cost N times. Dark, however, is a separate design pass
that benefits from focused review.

Ready to proceed to `sdd-propose: phase-4b-web-taxonomy-pages` once
the user ratifies (or amends) the 14 decisions above.

---

## Return Envelope

**Status**: success
**Executive summary**: Exploration of `phase-4b-web-taxonomy-pages`
complete. Surfaced 16 open questions, 12 risks, and 14 decisions for
user ratification. Verified API contract reality: `Note/Accord/Brand/
Perfumer/Article` detail schemas are leaner than nominal scope (no
bio, no description, no topics fields), which de-risks design but
constrains how editorial detail pages can be framed. Verified library
state via Context7 for `react-markdown@9` (ESM-only, RSC-compatible,
recommend with `remark-gfm` + `rehype-sanitize`) and `next-themes`
(class-based theme attribute, `enableSystem` for K1 path). Recommend
**ship 4b unified for the 10 pages and defer dark theme to phase 4c**.
**Artifacts**: `openspec/changes/phase-4b-web-taxonomy-pages/exploration.md`
**Next**: `sdd-propose: phase-4b-web-taxonomy-pages` (after user
ratifies the 14 decisions).
**Risks**: 12 documented (R1 markdown bundle; R2 thin pages; R3 tree
DOM weight; R4 dark contrast (deferred); R5 XSS; R6 partial deploy;
R7 sitemap blowup; R8 type-gen drift; R9 empty taxonomy; R10 spec
word budget; R11 ESM transpile; R12 notFound on detail).
**Skill Resolution**: fallback-path — read `sdd-explore/SKILL.md` and
`_shared/sdd-phase-common.md` + `_shared/openspec-convention.md` from
the global skills directory.
