# fragrance-catalog-ui Specification

## Purpose

Defines the catalog spine of `apps/web/`: home page, fragrance list (with URL-driven filters and pagination), fragrance detail (with notes pyramid), shared site shell (header + footer + skip-to-content + mobile drawer), image fallback, glossary popovers, ISR caching posture, sitemap and robots, and the typed API client backing all of it.

## Requirements

### Pages

### Requirement: Home Page Renders Brand, Hero, Featured Strip, Footer

`apps/web/app/(site)/page.tsx` MUST render: the brand "Fragwise" in the display font, a hero section with a one-line tagline, a "discover by mood" tile grid linking to `/accords/[slug]` (links MUST resolve to 200 in 4a, either via 4b routes or via `/fragrances?accord=<slug>` filtered fallback), a "featured fragrances" strip with at least four `FragranceCard`s populated from the live API, a "from the journal" placeholder teaser, and the site footer. ISR MUST revalidate every 600 seconds.

#### Scenario: Home renders core sections

- GIVEN the dev server is running with the API reachable
- WHEN a client requests `GET /`
- THEN the rendered HTML contains "Fragwise"
- AND it contains hero tagline copy
- AND it contains at least four `FragranceCard` instances under a "featured fragrances" heading
- AND it contains the footer with GitHub, License, and Contributing links

#### Scenario: Home page revalidates on a 10-minute window

- GIVEN the home page server component
- WHEN inspecting the data fetch options
- THEN at least one fetch call passes `next: { revalidate: 600 }`

### Requirement: Fragrance List Page With URL-Driven Filters And Pagination

`apps/web/app/(site)/fragrances/page.tsx` MUST render a responsive grid of `FragranceCard`s (1 col `<sm`, 2 `sm`, 3 `md`, 4 `lg`), a collapsible filter sidebar, and a numbered pagination control. Filter and pagination state MUST live in URL `searchParams`: `gender`, `accord` (multi), `brand`, `year_min`, `year_max`, `concentration`, `note` (multi), `limit`, `offset`. ISR MUST revalidate every 300 seconds and the cache key MUST include serialized `searchParams`. The page MUST include a `loading.tsx` skeleton state and a zero-result empty state.

#### Scenario: Filter applied via sidebar updates URL and grid

- GIVEN the list page is rendered
- WHEN the user selects an accord chip in the sidebar
- THEN the URL updates to include `?accord=<slug>`
- AND the grid re-renders with only fragrances matching that accord

#### Scenario: Pagination navigates via URL offset

- GIVEN a list with more results than `limit`
- WHEN the user clicks page 2 in the pagination control
- THEN the URL updates `?offset` to `limit`
- AND the grid renders the next page of results

#### Scenario: Filter combination with zero matches shows empty state

- GIVEN filters whose intersection returns no fragrances
- WHEN the page renders
- THEN an empty-state component is shown (not an empty grid)
- AND a "clear filters" link is visible

#### Scenario: Clear filters strips URL params

- GIVEN one or more filters are active in the URL
- WHEN the user activates "clear all"
- THEN every filter `searchParam` is removed from the URL
- AND the grid renders the unfiltered first page

#### Scenario: List uses 5-minute ISR

- GIVEN the list page server component
- WHEN inspecting the data fetch options
- THEN at least one fetch call passes `next: { revalidate: 300 }`

### Requirement: Fragrance Detail Page With Pyramid And Fallback

`apps/web/app/(site)/fragrances/[slug]/page.tsx` MUST render: a split hero (bottle image or fallback on the left, name + brand + perfumer credits on the right, accord/gender/year metadata strip), a `Pyramid` component showing top/heart/base notes, a description section, an articles list with empty state, and a "more from this brand" carousel placeholder. Unknown slugs MUST render the `not-found.tsx` page. ISR MUST revalidate every 600 seconds and MUST tag the fetch with `fragrance:{slug}`.

#### Scenario: Valid slug renders full layout

- GIVEN a fragrance exists in the API with slug `s`
- WHEN a client requests `GET /fragrances/s`
- THEN the page renders the hero, pyramid, description, and articles section
- AND the response status is 200

#### Scenario: Unknown slug renders not-found

- GIVEN no fragrance exists for slug `does-not-exist`
- WHEN a client requests `GET /fragrances/does-not-exist`
- THEN the response renders the custom not-found page
- AND the response status is 404

#### Scenario: Image-less fragrance renders intentional fallback

- GIVEN a fragrance whose `image_url` is null
- WHEN the detail page renders
- THEN the `ImageFallback` component is rendered in the bottle slot
- AND no broken-image icon or empty box is visible

#### Scenario: Detail uses 10-minute ISR with cache tag

- GIVEN the detail page server component for slug `s`
- WHEN inspecting the data fetch options
- THEN the fetch passes `next: { revalidate: 600, tags: ['fragrance:s'] }`

### Components

### Requirement: Site Header Sticky With Disabled Search And Mobile Drawer

`Header` MUST be sticky at the top of `app/(site)/layout.tsx`, contain a logo linking to `/`, primary nav with links Home and Fragrances plus placeholder labels for Notes, Accords, Brands, Perfumers, and Articles, and a disabled search input with placeholder text such as "Search coming soon". On viewports `<md`, the nav MUST move into a `sheet` drawer toggled by a hamburger button.

#### Scenario: Header renders sticky with disabled search

- GIVEN any page under the `(site)` route group
- WHEN the page renders
- THEN the header has CSS `position: sticky` and is the topmost focusable region (after skip-to-content)
- AND a search `<input disabled>` with the placeholder text is present

#### Scenario: Mobile drawer opens nav

- GIVEN viewport width is `<md`
- WHEN the user activates the hamburger button
- THEN a `sheet` drawer opens containing the same nav links

### Requirement: Footer With GitHub, License, And Contributing Links

`Footer` MUST render: a link to the project's GitHub repository, a link to the Apache-2.0 LICENSE, a link to the Contributing guide, and a copyright line.

#### Scenario: Footer links present

- GIVEN any page under `(site)`
- WHEN inspecting the footer
- THEN it contains anchors with hrefs for GitHub, License, and Contributing

### Requirement: Skip-To-Content Link First Focusable In Layout

A `SkipToContent` link MUST be the first focusable element in `app/(site)/layout.tsx` and MUST target a `#main-content` anchor wrapping the page content.

#### Scenario: Tab focus reaches skip link first

- GIVEN any page under `(site)`
- WHEN a user presses Tab from page load
- THEN the first focusable element is the skip-to-content link
- AND activating it moves focus to `#main-content`

### Requirement: FragranceCard Renders Image, Brand, Name, Year, Gender, Accords

`FragranceCard` MUST render: an image slot (using `ImageFallback` when `image_url` is null), brand name in small type above fragrance name in larger type, year, a gender icon from `lucide-react`, and 1-3 accord chips. The entire card MUST be a single keyboard-focusable link with a visible focus ring.

#### Scenario: Card renders all required fields

- GIVEN a fragrance object with image, brand, name, year, gender, and accords
- WHEN `FragranceCard` is rendered
- THEN the image, brand, name, year, gender icon, and at least one accord chip are visible

#### Scenario: Card is keyboard-accessible

- GIVEN the card is rendered in a list
- WHEN the user tabs to the card and presses Enter
- THEN the browser navigates to `/fragrances/{slug}`
- AND the card displays a visible focus ring while focused

### Requirement: ImageFallback Renders Deterministic Color Panel With Initial

`ImageFallback` MUST render a colored panel whose hue is derived deterministically from a hash of the fragrance slug, plus a centered first-letter glyph in the display font with contrast-appropriate color (white on dark hues, dark on light hues). The same slug MUST always produce the same hue.

#### Scenario: Same slug yields same color

- GIVEN slug `s`
- WHEN `ImageFallback` is rendered twice with that slug
- THEN both renders produce identical background color values

#### Scenario: First letter glyph rendered

- GIVEN slug `chanel-no-5`
- WHEN `ImageFallback` is rendered
- THEN the first letter of the fragrance name is centered in the display font

### Requirement: Pyramid Renders Notes By Role With Empty Placeholder

`Pyramid` MUST render notes grouped into top, heart, and base rows in that order, with note names visible. Roles with zero notes MUST render an "—" placeholder rather than collapsing.

#### Scenario: All three roles populated

- GIVEN a fragrance with top, heart, and base notes
- WHEN `Pyramid` is rendered
- THEN three labeled rows appear with each note's name visible

#### Scenario: Missing role renders dash placeholder

- GIVEN a fragrance with only top and base notes
- WHEN `Pyramid` is rendered
- THEN the heart row is present and contains an "—" placeholder

### Requirement: Pagination Is URL-Driven With Boundary-Disabled Controls

`Pagination` MUST update the page via the URL `?offset=` parameter. The Previous control MUST be disabled when `offset === 0`; the Next control MUST be disabled when `offset + limit >= total`.

#### Scenario: Click page N updates URL offset

- GIVEN pagination is rendered with `total=120`, `limit=24`, `offset=0`
- WHEN the user clicks the page-3 link
- THEN the URL updates to include `?offset=48`

#### Scenario: Boundaries disable Prev/Next

- GIVEN `offset=0`
- THEN Previous is disabled
- GIVEN `offset + limit >= total`
- THEN Next is disabled

### Requirement: FilterSidebar Syncs With searchParams And Supports Clear-All

`FilterSidebar` MUST collapse filter groups via the `accordion` primitive, render currently-active filters as removable chips, mirror the URL `searchParams`, and expose a "clear all" link that strips every filter param.

#### Scenario: Active filter shown as chip

- GIVEN URL contains `?accord=woody`
- WHEN the sidebar renders
- THEN a chip for "woody" is visible
- AND clicking the chip's remove control strips `accord=woody` from the URL

#### Scenario: Clear-all strips every filter param

- GIVEN URL contains multiple filter params
- WHEN the user activates "clear all"
- THEN every filter param is removed from the URL while preserving non-filter params

### Requirement: Glossary Popover Wrapper Renders Underlined-Dotted Term

The `Glossary` component MUST wrap a jargon term, render it with a dotted underline, and on click, tap, or keyboard activation display a popover containing the term's definition. The popover MUST be triggerable consistently across pointer (click), touch (tap), and keyboard (Enter/Space) input. Hover-only triggering is NOT required because the underlying Radix `Popover` primitive opens on click/tap rather than hover.

#### Scenario: Click or tap shows popover with definition

- GIVEN a `Glossary` wraps the term "sillage"
- WHEN the user clicks, taps, or activates the term via keyboard
- THEN a popover appears containing the definition for "sillage"

#### Scenario: Term renders with dotted underline

- GIVEN a `Glossary` is rendered
- WHEN inspecting the rendered HTML/CSS
- THEN the term is styled with a dotted underline

### Data And Types

### Requirement: Generated API Types From OpenAPI

`apps/web/lib/api/types.ts` MUST exist and MUST be generated from `apps/api/openapi.json` via `openapi-typescript`. A CI gate MUST fail when the committed `types.ts` does not match the regenerated output.

#### Scenario: Generated types tracked and current

- GIVEN `apps/api/openapi.json` is current
- WHEN running the type-generation script
- THEN `apps/web/lib/api/types.ts` is regenerated
- AND `git diff --exit-code apps/web/lib/api/types.ts` exits 0 in CI

### Requirement: Typed openapi-fetch Client

`apps/web/lib/api/client.ts` MUST export a typed `openapi-fetch` client (`createClient<paths>({ baseUrl })`) configured with `process.env.NEXT_PUBLIC_API_URL`.

#### Scenario: Client exports typed instance

- GIVEN `apps/web/lib/api/client.ts`
- WHEN imported
- THEN it exports a value created via `createClient<paths>` from `openapi-fetch`
- AND `baseUrl` is read from `NEXT_PUBLIC_API_URL`

### Requirement: Typed Fetcher Helpers Pass Next.js Cache Options

`apps/web/lib/api/fetchers.ts` MUST export at least `getFragrances`, `getFragranceBySlug`, and `getFeaturedFragrances`, each typed against the generated `paths` and each passing the appropriate `next: { revalidate, tags }` options.

#### Scenario: getFragranceBySlug applies cache tag

- GIVEN slug `s`
- WHEN `getFragranceBySlug('s')` is invoked from a server component
- THEN the underlying fetch call is made with `next.revalidate === 600` and `next.tags` containing `fragrance:s`

### Requirement: Glossary Seed Terms Module

`apps/web/lib/glossary.ts` MUST export a map of approximately 12 terms with definitions, drawn from: sillage, accord, drydown, chypre, fougère, oriental, gourmand, aquatic, EDT, EDP, EDC, parfum, top notes, heart notes, base notes.

#### Scenario: Glossary module exports ~12 terms

- GIVEN `apps/web/lib/glossary.ts`
- WHEN imported
- THEN the exported map contains between 10 and 14 entries
- AND each entry has a non-empty `term` and `definition`

### Sitemap And Robots

### Requirement: Sitemap Lists Home, List, And Fragrance Slugs

`apps/web/app/sitemap.ts` MUST emit entries for `/`, `/fragrances`, and one entry per fragrance slug returned by the API at build time.

#### Scenario: Sitemap contains fragrance slugs

- GIVEN the API exposes N fragrance slugs at build time
- WHEN `next build` runs
- THEN the generated `sitemap.xml` contains entries for `/`, `/fragrances`, and N `/fragrances/[slug]` URLs

### Requirement: Robots Allows All And References Sitemap

`apps/web/app/robots.ts` MUST allow user-agent `*` and reference the sitemap URL.

#### Scenario: robots.txt allows all and points to sitemap

- GIVEN `next build` has run
- WHEN fetching `/robots.txt`
- THEN the body contains `User-agent: *` and `Allow: /` (or equivalent)
- AND a `Sitemap:` line points to the generated sitemap URL

### Tests

### Requirement: Vitest Render Tests For Catalog Components

Vitest tests MUST render `FragranceCard`, `ImageFallback` (asserting color determinism for the same slug), `Pyramid` (with all roles populated AND with one role missing), `Pagination` (asserting boundary-disabled state), and `Glossary` (asserting popover presence on activation).

#### Scenario: Required test files exist and pass

- GIVEN `apps/web/__tests__/`
- WHEN running `pnpm --filter web test`
- THEN tests for each of the listed components run
- AND the suite exits 0

### Requirement: Playwright Smoke Updates For New Pages

The existing `apps/web/e2e/home.spec.ts` MUST assert the brand string and the "featured fragrances" strip. New `apps/web/e2e/fragrances.spec.ts` MUST assert that pagination advances and a filter narrows the grid. New `apps/web/e2e/fragrance-detail.spec.ts` MUST assert the notes pyramid renders. All Playwright specs MUST remain manual-trigger only.

#### Scenario: Playwright smoke specs cover the three pages

- GIVEN a running dev server with the API reachable
- WHEN Playwright executes the three specs via `workflow_dispatch`
- THEN each spec asserts its required behavior and exits 0
- AND no Playwright job runs on `push` or `pull_request` triggers

### Taxonomy Pages (Phase 4b)

### Requirement: Notes Tree Page

`apps/web/app/(site)/notes/page.tsx` MUST render the full note hierarchy returned by `GET /api/v1/notes` as a recursive shadcn `Accordion` (the `NoteTree` component). All top-level branches MUST be collapsed by default on first paint. Clicking a branch MUST expand its children client-side without a server round-trip.

#### Scenario: Tree renders with all branches collapsed

- GIVEN the API returns a `NoteTreeNode[]` with N top-level branches
- WHEN `GET /notes` renders
- THEN N `AccordionItem` headers are visible
- AND no child nodes are visible until a branch is opened

#### Scenario: Branch expansion is client-side

- GIVEN the tree has rendered
- WHEN the user clicks a top-level branch header
- THEN that branch's children become visible
- AND no full page navigation occurs

### Requirement: Note Detail Page

`apps/web/app/(site)/notes/[slug]/page.tsx` MUST render: the note name, a parent breadcrumb when `parent` is non-null, a child notes list when children exist, and a paginated `FragranceCard` grid of fragrances that feature this note (sourced from `NoteDetail.fragrances`). On unknown slug the route MUST call `notFound()`.

#### Scenario: Note with parent and children

- GIVEN a note `s` with a `parent` slug `p` and 2 child notes
- WHEN `GET /notes/s` renders
- THEN the page shows the note name and a breadcrumb linking to `/notes/p`
- AND a child notes list is visible with links to each child slug

#### Scenario: Fragrance grid is paginated

- GIVEN a note with more fragrances than `limit`
- WHEN `GET /notes/s?offset=24` renders
- THEN the grid shows the next page of fragrances
- AND `Pagination` is present with URL-driven offset

#### Scenario: Unknown slug returns 404

- GIVEN no note exists for slug `bogus`
- WHEN `GET /notes/bogus` renders
- THEN `notFound()` is invoked and the response status is 404

### Requirement: Accords Grid Page

`apps/web/app/(site)/accords/page.tsx` MUST render every accord family returned by `GET /api/v1/accords` as a grid of `AccordCard` components (one per accord). Each card MUST link to `/accords/[slug]`.

#### Scenario: Accord grid renders one card per accord

- GIVEN the API returns N accords
- WHEN `GET /accords` renders
- THEN N `AccordCard` instances are visible in a grid
- AND each card's anchor href equals `/accords/<slug>`

### Requirement: Accord Detail Page With Hand-Authored Blurb

`apps/web/app/(site)/accords/[slug]/page.tsx` MUST render: a hand-authored blurb sourced from `apps/web/lib/accord-copy.ts` for the matching slug (with optional `<Glossary>` popovers), followed by a paginated `FragranceCard` grid of fragrances tagged with that accord (from `AccordDetail.fragrances`). When no blurb is registered for the slug, the page MUST still render with name + grid (no error). On unknown slug from the API the route MUST call `notFound()`.

#### Scenario: Accord with curated blurb

- GIVEN `lib/accord-copy.ts` exports a blurb for accord `woody`
- WHEN `GET /accords/woody` renders
- THEN the rendered HTML contains the blurb text above the fragrance grid
- AND any `<Glossary>` term inside the blurb activates its popover on click

#### Scenario: Accord without registered blurb

- GIVEN `lib/accord-copy.ts` has no entry for accord `mossy`
- WHEN `GET /accords/mossy` renders
- THEN the page renders the accord name and fragrance grid
- AND no blurb section is present

#### Scenario: Unknown accord slug returns 404

- GIVEN the API returns 404 for accord `bogus`
- WHEN `GET /accords/bogus` renders
- THEN `notFound()` is invoked and the response status is 404

### Requirement: Brands List Page With Q-Search

`apps/web/app/(site)/brands/page.tsx` MUST render a paginated `BrandCard` list backed by `GET /api/v1/brands` (offset/limit). It MUST include a `SearchInput` client component that debounces user input (~300 ms) and updates the URL `?q=` searchParam. The server reads `q` and forwards it to the API. The match is a case-insensitive ILIKE substring on brand name. A malformed escape pattern (e.g., bare `%` not produced by the canonicalizer) MUST surface as a 422 from the API; the page MUST render its empty/error state without crashing.

#### Scenario: q updates URL and filters list

- GIVEN the user types "cha" into `SearchInput`
- WHEN ~300 ms elapse without further input
- THEN the URL gains `?q=cha`
- AND the rendered list shows only brands whose name matches case-insensitive substring "cha"

#### Scenario: API 422 on malformed q renders empty state

- GIVEN the API responds 422 to a malformed `?q=%` payload
- WHEN the page renders
- THEN no exception bubbles to the user
- AND an empty/error state is shown

#### Scenario: Pagination present without q

- GIVEN no `q` in the URL
- WHEN `GET /brands` renders
- THEN `BrandCard` items render in a list
- AND `Pagination` is present with URL-driven offset

### Requirement: Brand Detail Page

`apps/web/app/(site)/brands/[slug]/page.tsx` MUST render the brand name in editorial typography and a paginated `FragranceCard` grid of fragrances under that brand (from `BrandDetail.fragrances`). On unknown slug the route MUST call `notFound()`.

#### Scenario: Brand renders header and paginated grid

- GIVEN brand `s` has 50 fragrances
- WHEN `GET /brands/s` renders
- THEN the brand name appears in the page header
- AND the first page of `FragranceCard` items is visible
- AND `Pagination` is present with URL-driven offset

#### Scenario: Unknown slug returns 404

- GIVEN no brand exists for slug `bogus`
- WHEN `GET /brands/bogus` renders
- THEN `notFound()` is invoked and the response status is 404

### Requirement: Perfumers List Page With Q-Search

`apps/web/app/(site)/perfumers/page.tsx` MUST render a paginated `PerfumerCard` list backed by `GET /api/v1/perfumers` (offset/limit) and MUST mirror the brands list page shape: a `SearchInput` driving `?q=` (debounced ~300 ms), case-insensitive ILIKE substring filter, and `Pagination`.

#### Scenario: q updates URL and filters list

- GIVEN the user types "ell" into `SearchInput`
- WHEN ~300 ms elapse without further input
- THEN the URL gains `?q=ell`
- AND the rendered list shows only perfumers whose name matches case-insensitive substring "ell"

#### Scenario: Pagination present without q

- GIVEN no `q` in the URL
- WHEN `GET /perfumers` renders
- THEN `PerfumerCard` items render in a list
- AND `Pagination` is present with URL-driven offset

### Requirement: Perfumer Detail Page

`apps/web/app/(site)/perfumers/[slug]/page.tsx` MUST render the perfumer name and a paginated `FragranceCard` grid of fragrances they made (from `PerfumerDetail.fragrances`). On unknown slug the route MUST call `notFound()`.

#### Scenario: Perfumer renders header and paginated grid

- GIVEN perfumer `s` has fragrances credited to them
- WHEN `GET /perfumers/s` renders
- THEN the perfumer name appears in the page header
- AND `FragranceCard` items render in a grid
- AND `Pagination` is present with URL-driven offset

#### Scenario: Unknown slug returns 404

- GIVEN no perfumer exists for slug `bogus`
- WHEN `GET /perfumers/bogus` renders
- THEN `notFound()` is invoked and the response status is 404

### Requirement: Articles List Page

`apps/web/app/(site)/articles/page.tsx` MUST render a paginated list of `ArticleCard` items, ordered by `published_at DESC` as returned by `GET /api/v1/articles`. Each card MUST display the article title, the relative published time, and link to `/articles/[slug]`.

#### Scenario: Articles ordered by published_at desc

- GIVEN the API returns articles ordered by `published_at DESC`
- WHEN `GET /articles` renders
- THEN the cards appear in the same order
- AND each card href equals `/articles/<slug>`

#### Scenario: Pagination is URL-driven

- GIVEN the article count exceeds `limit`
- WHEN the user navigates to page 2
- THEN the URL `?offset` updates and the next page renders

### Requirement: Article Detail Page With Markdown Body

`apps/web/app/(site)/articles/[slug]/page.tsx` MUST render the article title, the `published_at` timestamp, and the `body` field through the `<ArticleBody>` component (markdown + sanitize stack defined in design-system). On unknown slug the route MUST call `notFound()`.

#### Scenario: Article detail renders markdown body

- GIVEN an article `s` with non-null body
- WHEN `GET /articles/s` renders
- THEN the page shows the title and published date
- AND the body is rendered via `<ArticleBody>` (sanitized markdown output)

#### Scenario: Unknown slug returns 404

- GIVEN no article exists for slug `bogus`
- WHEN `GET /articles/bogus` renders
- THEN `notFound()` is invoked and the response status is 404
