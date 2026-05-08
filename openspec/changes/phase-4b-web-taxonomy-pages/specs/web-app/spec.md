# Delta for web-app

## ADDED Requirements

### Requirement: Taxonomy Routes Available

The web app MUST expose ten new App Router routes under `apps/web/app/(site)/`: `/notes`, `/notes/[slug]`, `/accords`, `/accords/[slug]`, `/brands`, `/brands/[slug]`, `/perfumers`, `/perfumers/[slug]`, `/articles`, `/articles/[slug]`. Each list route MUST resolve with status 200 against the live API. Each detail route MUST call Next's `notFound()` (rendering a 404) when the API responds 404 for that slug.

#### Scenario: List routes return 200

- GIVEN the dev server is running with the API reachable
- WHEN a client requests each of `/notes`, `/accords`, `/brands`, `/perfumers`, `/articles`
- THEN every response status is 200
- AND each rendered HTML body contains the page heading

#### Scenario: Detail route with valid slug returns 200

- GIVEN a slug `s` exists for a given resource
- WHEN a client requests `GET /<resource>/s` (one of notes, accords, brands, perfumers, articles)
- THEN the response status is 200
- AND the page renders the resource's name or title

#### Scenario: Detail route with unknown slug returns 404

- GIVEN no resource exists for slug `does-not-exist`
- WHEN a client requests `GET /<resource>/does-not-exist`
- THEN the route file invokes `notFound()`
- AND the response status is 404

### Requirement: Article Markdown Rendering

`/articles/[slug]` MUST render the article `body` field through `react-markdown` configured with `remark-gfm` (GFM extensions) and `rehype-sanitize` (sanitize stage). The sanitize schema MUST drop `<script>`, `<iframe>`, and event-handler attributes (`on*`). The schema MUST allow code blocks, tables, lists, and links; rendered links MUST carry `rel="noopener noreferrer"` and `target="_blank"`.

#### Scenario: Markdown body parsed with GFM and sanitize

- GIVEN an article body containing GFM table syntax and a fenced code block
- WHEN the article detail page renders
- THEN the table renders as `<table>` with rows
- AND the fenced code renders as `<pre><code>`

#### Scenario: Script tag stripped by sanitize

- GIVEN an article body containing `<script>alert(1)</script>` injected by an upstream pipeline
- WHEN the article detail page renders
- THEN the rendered HTML contains no `<script>` element
- AND no `on*=` event handler attribute is present in the rendered output

#### Scenario: External link gets safe rel and target

- GIVEN an article body with `[link](https://example.com)`
- WHEN rendered
- THEN the anchor element has `rel="noopener noreferrer"` and `target="_blank"`

### Requirement: Glossary Scope For Accord Blurbs

Hand-authored accord blurbs in `apps/web/lib/accord-copy.ts` MAY use the `<Glossary>` wrapper to annotate jargon. Article markdown bodies MUST render as raw markdown without automatic `<Glossary>` wrapping; no markdown-AST glossary transform may be applied in 4b.

#### Scenario: Accord blurb may wrap a term

- GIVEN an accord blurb in `lib/accord-copy.ts` wraps the term "sillage" with `<Glossary>`
- WHEN `/accords/[slug]` renders
- THEN the term displays with the dotted underline and popover wiring

#### Scenario: Article body renders without glossary wrap

- GIVEN an article body contains plain text "sillage"
- WHEN `/articles/[slug]` renders
- THEN no `<Glossary>` wrapper is injected around the term
- AND no glossary popover is registered for it

### Requirement: Sitemap Includes Taxonomy Slugs

`apps/web/app/sitemap.ts` MUST include all known slugs at build time for the five new resource types: notes, accords, brands, perfumers, articles. Each fetcher loop MUST cap iteration with an upper bound `MAX_PAGES = 200` so that a runaway dataset cannot bloat the sitemap unboundedly.

#### Scenario: Sitemap enumerates each taxonomy resource

- GIVEN the API exposes slugs for notes, accords, brands, perfumers, and articles at build time
- WHEN `next build` runs
- THEN `/sitemap.xml` contains entries under `/notes/[slug]`, `/accords/[slug]`, `/brands/[slug]`, `/perfumers/[slug]`, and `/articles/[slug]`

#### Scenario: MAX_PAGES caps each loop

- GIVEN a resource fetcher loop in `app/sitemap.ts`
- WHEN inspecting the source
- THEN the iteration condition is bounded by a `MAX_PAGES = 200` constant
- AND the loop terminates without overflow even if the API returns more than 200 pages

### Requirement: NAV Feature-Flag Map

The Header and MobileMenu components MUST import a `NAV` constant from `apps/web/lib/site-nav.ts`. Each entry MUST have shape `{ href: string, label: string, ready: boolean }`. Items where `ready === true` MUST render as a Next `<Link>` with `aria-current="page"` applied when the current pathname matches. Items where `ready === false` MUST render as a `<span aria-disabled="true">` carrying `title="Coming with phase 4c+"`.

#### Scenario: Ready item renders as link with aria-current

- GIVEN the NAV map flags `/notes` as `ready: true`
- WHEN the Header renders on the `/notes` route
- THEN the Notes nav item is a `<Link href="/notes">` with `aria-current="page"`

#### Scenario: Not-ready item renders as disabled span

- GIVEN the NAV map flags an item as `ready: false`
- WHEN the Header renders
- THEN that item is a `<span aria-disabled="true">` with `title="Coming with phase 4c+"`
- AND it is not a focusable link

## MODIFIED Requirements

### Requirement: Brand Visible On Home Page

`apps/web/app/(site)/page.tsx` MUST render the literal string "Fragwise" as primary heading content using the display font, alongside the home structure: a hero section with a one-line tagline, a "discover by mood" tile grid whose hrefs link to `/accords/[slug]` (each MUST resolve to 200 against the live `/accords/[slug]` route shipped in 4b), a "featured fragrances" strip with at least four `FragranceCard` instances populated from the live API, a "from the journal" placeholder teaser, and the site footer.
(Previously: mood tile hrefs pointed to `/fragrances?accord=<slug>` as a 4a fallback because `/accords/[slug]` did not yet exist.)

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

#### Scenario: Mood tile hrefs target accord detail pages

- GIVEN the home page mood tile grid is rendered
- WHEN inspecting each tile anchor
- THEN every `href` matches `/accords/<slug>` (NOT `/fragrances?accord=<slug>`)
- AND clicking a tile navigates to a 200 response on `/accords/[slug]`
