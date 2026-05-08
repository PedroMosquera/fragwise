# Proposal: Phase 4b — Web Taxonomy Pages

## Intent

Phase 4a shipped the editorial perfumery shell with 3 pages live (`/`, `/fragrances`, `/fragrances/[slug]`) and 5 NAV placeholders rendered as `aria-disabled` spans. 4b activates the remaining catalog surface: notes, accords, brands, perfumers, and articles — 10 routes total — so the Header NAV becomes meaningful, mood tiles deep-link to curated accord pages, and journal content is reachable. The OpenAPI contract (P1) for these resources is locked and lean (no `bio`, `description`, or `topics` fields), which scopes 4b to "list + detail with editorial framing" rather than rich biography rendering.

## Scope

### In Scope

- **10 routes** under `apps/web/app/(site)/`: notes (tree + detail), accords (grid + detail), brands (searchable list + detail), perfumers (searchable list + detail), articles (list + detail with markdown body).
- **7 new components**: `taxonomy/{NoteTree,AccordCard,BrandCard,PerfumerCard}.tsx`, `editorial/{ArticleCard,ArticleBody}.tsx`, `site/SearchInput.tsx`.
- **2 new lib files**: `lib/accord-copy.ts` (6 hand-authored blurbs), `lib/site-nav.ts` (NAV feature-flag map).
- **Fetcher extensions**: 9 new helpers in `lib/api/fetchers.ts` (notes tree, accord/brand/perfumer/article slug lookups, paginated lists).
- **Header / MobileMenu**: import NAV from `lib/site-nav.ts`; render `ready: true` items as `<Link>`, `ready: false` as `<span aria-disabled>`. Flip 5 placeholders to `ready: true` once routes land.
- **Home page**: mood tile hrefs → `/accords/<slug>`; "From the journal" teaser activated.
- **Sitemap**: add brand/perfumer/accord/note/article slugs with `MAX_PAGES` guard.
- **Markdown stack**: `react-markdown@9` + `remark-gfm@4` + `rehype-sanitize@6` for `/articles/[slug]`.
- **Per-detail `generateMetadata`**, vitest render tests, Playwright smoke for new routes.

### Out of Scope

- Dark theme (deferred to phase 4c per D-DarkTheme; ADR-0037).
- Functional Header search (waits for chat / P2 wiring).
- Brand/perfumer biography enrichment (API lacks `bio`).
- Article topics/tags (API lacks `topics`).
- Note tree pagination (D-NotesPagination — accordion collapse handles DOM weight).
- Compact-list alternate for brand/perfumer detail (D-DetailLayout).
- Auto glossary wrapping inside article markdown (D-Glossary — manual on accord blurbs only).

## Capabilities

### New Capabilities

- None. All ten routes belong to existing capabilities.

### Modified Capabilities

- `web-app`: ~5 ADDED requirements (taxonomy routes resolve to 200, article markdown rendering, glossary scope, sitemap completeness, NAV feature-flag promotion) + 1 MODIFIED (mood tile hrefs).
- `fragrance-catalog-ui`: ~10 ADDED requirements (one per new route family + article body shape + accord blurb).
- `design-system`: 1 ADDED requirement (markdown stack ships in 4b; tokens unchanged).

## Approach

Per exploration `## Recommendation`, ship 10 pages unified — they share fetcher block, NAV map, sitemap edit, and generated types. Reuse 4a primitives (`FragranceCard`, `Pagination`, `Container`, `Glossary`, `ImageFallback`) so new routes inherit the editorial language. Brand/perfumer detail pages reuse the FragranceCard grid under an editorial header (D-DetailLayout). Accord detail is standalone with hand-authored blurbs (D-AccordDetail). Note tree is recursive shadcn `Accordion`, all branches collapsed (D-NoteTree, exploration Q3-T1). NAV promotion is gated by `lib/site-nav.ts` feature flags (D-NavPromotion, exploration Q9-N3) so partial-deploy states never expose broken links. Brand/perfumer search is debounced URL `?q=` only (D-PerPageSearch, exploration Q12-U1). All detail pages call `notFound()` on 404 and ship `generateMetadata` (D-Metadata).

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `apps/web/app/(site)/{notes,accords,brands,perfumers,articles}/**` | New | 10 route files + loading.tsx where useful |
| `apps/web/components/taxonomy/`, `apps/web/components/editorial/` | New | 6 new components |
| `apps/web/components/site/{Header,MobileMenu,SearchInput}.tsx` | Modified/New | NAV reads from feature-flag map; SearchInput new |
| `apps/web/app/(site)/page.tsx` | Modified | Mood tile hrefs + journal teaser |
| `apps/web/app/sitemap.ts` | Modified | Append 5 resource loops with `MAX_PAGES` cap |
| `apps/web/lib/api/fetchers.ts` | Modified | +9 fetchers |
| `apps/web/lib/{accord-copy,site-nav}.ts` | New | Hand-authored blurbs + NAV feature-flag map |
| `apps/web/package.json`, `pnpm-lock.yaml` | Modified | Add markdown deps |
| `openspec/specs/{web-app,fragrance-catalog-ui,design-system}/spec.md` | Modified (delta) | Spec deltas |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Markdown bundle bloat ~30 KB on `/articles/[slug]` (R1) | Med | Verify size-limit gate; dynamic import or drop GFM if breached |
| "Thin" brand/perfumer pages without `bio` (R2) | High | Editorial header hierarchy (Fraunces 5xl-7xl name, mono credit line); future API enrichment |
| Note tree DOM weight 200+ leaves (R3) | Med | All branches collapsed by default; SSR'd accordion |
| Article body XSS (R5) | Low | `rehype-sanitize` default schema; verify config matches markdown features |
| Header NAV partial-deploy state (R6) | Low | Feature-flag map (N3) prevents broken links |
| Generated types drift (R8) | Low | 4a CI gate already enforces |
| `notFound()` per detail slug (R12) | Low | Replicate 4a fragrance pattern across all 5 resources |
| Spec word budget 30-50 new reqs (R10) | Med | Group reqs by resource; `sdd-spec` plans an added/modified summary |
| `react-markdown` ESM-only (R11) | Low | Verify `transpilePackages` in `next.config.ts` during design |

## Rollback Plan

- **Pre-merge**: `git reset` on the feature branch.
- **Post-merge, pre-deploy**: revert merge commit; CI re-runs cleanly (no migrations).
- **Post-deploy**: revert deploy; cache rolls over within `revalidate` windows (600-3600s). No DB or external-state mutations to undo.

## Dependencies

- **External**: `react-markdown@9`, `remark-gfm@4`, `rehype-sanitize@6` (all ESM-only, RSC-compatible — Context7 verified during exploration).
- **Internal**: P1 `catalog-api` contract (locked); P4a primitives (FragranceCard, Pagination, Glossary, etc.).

## Success Criteria

- [ ] All 5 NAV items render as active `<Link>` after deploy.
- [ ] All 10 new routes return 200 (or 404 via `notFound()` on bad slug) and render under both light theme and SSR.
- [ ] Mood tiles on `/` link to `/accords/<slug>`; clicks land on standalone curated pages.
- [ ] `/articles/[slug]` renders sanitized markdown without XSS leaks.
- [ ] Sitemap includes brand, perfumer, accord, note, and article slugs (capped at `MAX_PAGES` per loop).
- [ ] `generateMetadata` returns title and description on every detail page.
- [ ] Brand and perfumer list pages filter via debounced URL `?q=` without client-side state.
- [ ] vitest renders pass for all new components; Playwright smoke covers all 10 new routes.
- [ ] `.size-limit.json` budget honored on `/articles/[slug]`.
- [ ] No regressions in P4a routes (home, `/fragrances`, `/fragrances/[slug]`).
