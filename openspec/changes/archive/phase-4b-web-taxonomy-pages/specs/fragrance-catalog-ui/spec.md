# Delta for fragrance-catalog-ui

## ADDED Requirements

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
