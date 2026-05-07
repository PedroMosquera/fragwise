# Proposal: Phase 4a — Web Spine

## Intent

Graduate `apps/web/` from scaffold to a real, opinionated catalog UI: design-system foundations, typed API client, shared layout, and the three load-bearing pages (home, fragrance list, fragrance detail). Spine slice of Phase 4; supporting taxonomy/people pages defer to 4b.

## Scope

### In Scope
- API tooling: `openapi-typescript` (devDep) + `openapi-fetch` (dep); `scripts/generate-api-types.ts` reading `apps/api/openapi.json`; `pnpm generate-api-types` wired via `predev`/`prebuild`; `justfile` recipe.
- Typed client at `apps/web/lib/api/`: `client.ts` (configured `openapi-fetch`), `fetchers.ts` (typed read helpers w/ Next.js `revalidate` + `tags`).
- Design tokens: CSS variables (color, spacing, radii, shadows, type scale) in `apps/web/styles/`; light theme only.
- Fonts via `next/font/google`: Fraunces (display), Manrope (body), JetBrains Mono (labels) — tentative, frontend-design skill finalizes in design phase.
- 10 shadcn primitives added: `sheet`, `tooltip`, `accordion`, `command`, `skeleton`, `popover`, `scroll-area`, `breadcrumb`, `select`, `pagination`.
- Site shell: `Header` (sticky, disabled search input, light-only theme scaffold), `Footer`, `MobileMenu` (sheet), `Container`, `SkipToContent`.
- Catalog components: `FragranceCard`(+Skeleton), `Pyramid`, `AccordBadge`, `NoteBadge`, `ImageFallback` (slug-hashed colored panel + initial), `Pagination`, `FilterSidebar`.
- Glossary: `Glossary` tooltip wrapper + `lib/glossary.ts` seed terms (~12).
- Routes under `apps/web/app/(site)/`: `layout.tsx`, `page.tsx` (home), `fragrances/page.tsx` (list), `fragrances/[slug]/page.tsx` (detail), plus `loading.tsx`, `error.tsx`, `not-found.tsx`.
- ISR caching: home 10 min; list 5 min keyed by `searchParams`; detail 10 min + cache tag `fragrance:{slug}`. No `force-dynamic`.
- `app/sitemap.ts` (fragrance slugs from API at build) + `app/robots.ts`.
- Vitest render tests for new components; Playwright smoke updates assert home, list pagination/filter, detail pyramid.

### Out of Scope
- 4b pages: `/notes`, `/accords`, `/brands`, `/perfumers`, `/articles` (and details).
- Functional search (Phase 2), chatbot UI (Phase 3), dark theme (4b), Storybook, TanStack Query, i18n.

## Capabilities

### New Capabilities
- `design-system`: tokens, font config, theme provider, primitive set inventory.
- `fragrance-catalog-ui`: home, list (with filter/pagination), detail (with pyramid), shared shell, image fallback, glossary tooltips, ISR posture, sitemap/robots.

### Modified Capabilities
- `web-app`: add requirements for typed API client; light-theme tokens; ISR caching; URL-driven pagination; image fallback contract; glossary tooltip mechanism.

## Approach

RSC-only data fetching via `openapi-fetch`, leaning on Next.js `fetch` extensions for ISR + tag-based revalidation. Filter state lives in URL `searchParams`. Aesthetic direction is tentative editorial-perfumery; final palette/type call belongs to the `frontend-design` skill at design phase.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `apps/web/lib/api/` | New | Typed client + fetchers |
| `apps/web/components/site/` | New | Header, Footer, MobileMenu, Container, SkipToContent, Glossary |
| `apps/web/components/catalog/` | New | Cards, Pyramid, badges, Pagination, FilterSidebar, ImageFallback |
| `apps/web/components/ui/` | Modified | +10 shadcn primitives |
| `apps/web/app/(site)/` | New | Routes + layout + error boundaries |
| `apps/web/styles/`, `app/globals.css` | Modified | Tokens + Tailwind v4 theme mapping |
| `apps/web/scripts/generate-api-types.ts` | New | OpenAPI → types codegen |
| `apps/web/package.json`, `pnpm-lock.yaml` | Modified | Deps + scripts |
| `justfile` | Modified | `generate-types` recipe |
| `openspec/specs/web-app/` | Modified | Delta requirements |
| `openspec/specs/design-system/`, `fragrance-catalog-ui/` | New | New capability specs |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| R1 Generic AI design slop | High | `frontend-design` skill at design; `judgment-day` review pre-apply |
| R2 P1 API contract drift | Med | Design BLOCKS until P1 design archives contract section |
| R3 Image-less catalog reads broken | Med | Intentional slug-hashed fallback + initial letter |
| R4 Bundle bloat | Med | < 200 KB initial JS budget; verify `next build --analyze` in self-check |
| R5 ISR stale data | Low | Cache tags allow targeted purges in Phase 5 |
| R6 a11y regressions | Med | Radix primitives + manual keyboard/contrast pass |
| R7 Glossary scope creep | Low | Cap seed list at ~12 terms; design locks set |

## Rollback Plan

- Pre-merge: `git reset`.
- Post-merge / pre-deploy: revert merge commit (web has not deployed).
- Post-deploy: redeploy prior Vercel build.

## Dependencies

- **Phase 1 design** (catalog-read endpoints): MUST archive API contract (path shapes, envelope, filter syntax, error body, image URL host) before 4a `sdd-design` runs. 4a `sdd-spec` MAY run in parallel — specs describe UI acceptance criteria, not API specifics.
- Phase 0c R2 hostname must be confirmed for `images.remotePatterns`.
- `frontend-design` skill invoked at `sdd-design`; `judgment-day` review before `sdd-apply`.

## Success Criteria

- [ ] `pnpm --filter web build` succeeds; initial JS budget under 200 KB gzipped.
- [ ] `/`, `/fragrances`, `/fragrances/[slug]` render against live API with ISR active.
- [ ] Filter sidebar updates list via URL `searchParams`; pagination URL-driven.
- [ ] Image fallback renders on fragrances without R2 images and looks intentional.
- [ ] Glossary tooltips render on seed jargon terms with keyboard + touch access.
- [ ] Vitest + Playwright smoke pass; `tsc --noEmit` clean.
- [ ] WCAG 2.1 AA verified for shipped pages (contrast, focus order, alt text).
