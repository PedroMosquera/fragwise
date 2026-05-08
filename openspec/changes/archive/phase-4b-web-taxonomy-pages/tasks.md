# Tasks: Phase 4b — Web Taxonomy Pages

## Apply discipline (read first)

Per orchestrator retrospective on subagent quality:
1. **Smoke-import every new module** before marking the task done. Use `pnpm --filter web exec node -e "..."` or `tsx --eval "import('./...')"` — if it fails (circular import, missing export, syntax error), STOP and fix before moving on.
2. **Run `pnpm --filter web build`** after every batch of 3-5 tasks. If build fails, fix BEFORE the next task.
3. **For framework decisions, use Context7** (resolve-library-id then query-docs) — NOT training-data memory. Specifically verify at apply time:
   - `react-markdown@9` API + RSC compatibility
   - `rehype-sanitize@6` schema config (drop scripts/iframes/event handlers/style)
   - `remark-gfm@4` plugin order
   - Next.js 16 `transpilePackages` for ESM-only deps
4. **Output reporting discipline**: paste actual last 10 lines of `pnpm --filter web build`, `pnpm --filter web vitest run`, `pnpm --filter web exec tsc --noEmit`, `pnpm --filter web lint`.
5. **Sanitize XSS test is non-negotiable**: ArticleBody MUST drop `<script>`, `<iframe>`, every `on*` handler, and `style` attribute. Vitest negative test required.

## Phase 1: Pre-flight

- [x] 1.1 Confirm branch state: P4a archived (specs synced, change folder removed), `apps/web/lib/api/openapi.json` includes `/api/v1/{notes,accords,brands,perfumers,articles}` paths and matching schemas (`NoteTreeNode`, `NoteDetail`, `AccordDetail`, `BrandDetail`, `PerfumerDetail`, `ArticleSummary`, `ArticleDetail`). If any schema is missing, STOP — regenerate types via P1 contract before continuing. (~5 min)

## Phase 2: Dependencies

- [x] 2.1 Add to `apps/web/package.json` runtime `dependencies`: `react-markdown@^9`, `remark-gfm@^4`, `rehype-sanitize@^6`. Edit `apps/web/next.config.ts` per ADR-0049 to add `transpilePackages: ["react-markdown", "remark-gfm", "rehype-sanitize"]`. Run `pnpm install` to regenerate `pnpm-lock.yaml`. **Verify**: `pnpm --filter web build` produces no module resolution errors. (~10 min)

## Phase 3: Lib + NAV

- [x] 3.1 Create `apps/web/lib/site-nav.ts` per `design.md §"site-nav.ts"`. NAV feature-flag map with all 7 entries (Home, Fragrances, Notes, Accords, Brands, Perfumers, Journal) — all `ready: true` since 4b ships them. **Verify**: `pnpm --filter web exec tsx --eval "import('./lib/site-nav.ts').then(m => console.log(m.NAV.length))"` prints `7`. (~5 min)
- [x] 3.2 Create `apps/web/lib/accord-copy.ts` per `design.md §"accord-copy.ts"` (ADR-0046). Export `ACCORD_COPY` map with 6 hand-authored blurbs (woody, fougere, oriental, gourmand, aquatic, chypre). Each blurb 80–120 words, plain-string. **Verify**: smoke-import + `Object.keys(ACCORD_COPY).length === 6`. (~15 min)

## Phase 4: Fetcher additions

- [x] 4.1 Extend `apps/web/lib/api/fetchers.ts` with taxonomy fetchers per `design.md §"fetchers.ts extensions"`: `getAllNotes`, `getNoteBySlug`, `getAllAccords` (if missing — verify), `getAccordBySlug`. Apply ISR posture per ADR-0045 (notes:tree 3600s, note:slug 600s, accords:list 3600s, accord:slug 600s). All slug fetchers call `notFound()` on 404 per ADR-0046. **Verify**: `pnpm --filter web exec tsc --noEmit`. (~15 min)
- [x] 4.2 Extend same file with people + article fetchers: `getBrands`, `getBrandBySlug`, `getPerfumers`, `getPerfumerBySlug`, `getAllArticles`, `getArticleBySlug`. Brand/perfumer list revalidate is conditional (`hasQ ? 600 : 3600`). Brand/perfumer detail 1800s. Articles list+detail 600s. **Verify**: `pnpm --filter web exec tsc --noEmit`. (~20 min)

## Phase 5: Components — taxonomy

- [x] 5.1 Create `apps/web/components/taxonomy/NoteTree.tsx` per `design.md §"NoteTree.tsx"`. Recursive shadcn `Accordion` (type="multiple"), all branches collapsed by default. Branch click does NOT navigate (stopPropagation on inner Link). Leaf nodes render as plain `<Link>`. **Verify**: `pnpm --filter web exec tsc --noEmit`. (~20 min)
- [x] 5.2 Create `apps/web/components/taxonomy/{AccordCard,BrandCard,PerfumerCard}.tsx` per `design.md` paste-ready snippets. AccordCard is a tile (aspect-[5/3]); BrandCard / PerfumerCard are list rows with right arrow. **Verify**: smoke-import each module. (~15 min)

## Phase 6: Components — editorial + site

- [x] 6.1 Create `apps/web/components/editorial/ArticleCard.tsx` and `apps/web/components/editorial/ArticleBody.tsx` per `design.md`. ArticleBody MUST export named `SANITIZE_SCHEMA` const built from `defaultSchema` per ADR-0042 (drops script/iframe/object/embed/style/link/meta tags + every `on*` attr + `style` attr). Compose `react-markdown` with `remark-gfm` (remark) → `rehype-sanitize(SANITIZE_SCHEMA)` (rehype, last). Override `a` mapping per ADR-0043 to inject `rel="noopener noreferrer" target="_blank"` for external links. **Verify**: smoke-import; `pnpm --filter web build` succeeds. (~25 min)
- [x] 6.2 Create `apps/web/components/site/SearchInput.tsx` per `design.md §"SearchInput.tsx"` (ADR-0048). 300ms debounce, `useTransition` + `router.replace(?q=value, { scroll: false })`. Resets `?offset=` whenever `q` changes. Initial value from `useSearchParams().get(paramKey)`. **Verify**: smoke-import. (~15 min)

## Phase 7: Header + MobileMenu refactor

- [x] 7.1 Edit `apps/web/components/site/Header.tsx` and `apps/web/components/site/MobileMenu.tsx` per `design.md §"Header + MobileMenu modifications"`. Drop inline NAV array; `import { NAV, type NavItem } from "@/lib/site-nav"`. Render `<Link>` if `item.ready`, else `<span aria-disabled="true" title="Coming with phase 4c+">`. `aria-current="page"` via small `NavLink` client subcomponent reading `usePathname()` (preserves Header as RSC). **Verify**: `pnpm --filter web build`. (~20 min)

## Phase 8: Pages — notes

- [x] 8.1 Create `apps/web/app/(site)/notes/page.tsx` (list — uses `NoteTree`), `apps/web/app/(site)/notes/[slug]/page.tsx` (detail — breadcrumb, child list, FragranceCard grid + Pagination), `apps/web/app/(site)/notes/[slug]/loading.tsx` (skeleton per `design.md §"loading.tsx segments"`). Both pages export `metadata` / `generateMetadata`. Detail page calls `notFound()` via fetcher per ADR-0046. **Verify**: `curl -s localhost:3000/notes` returns 200. (~25 min)

## Phase 9: Pages — accords

- [x] 9.1 Create `apps/web/app/(site)/accords/page.tsx` (grid of `AccordCard`), `apps/web/app/(site)/accords/[slug]/page.tsx` per `design.md` (editorial header + `wrapGlossary(blurb, Glossary)` + paginated FragranceCard grid), `apps/web/app/(site)/accords/[slug]/loading.tsx`. Detail page handles missing blurb gracefully (renders header+grid only). `generateMetadata` uses blurb.slice(0, 160) when present. (~25 min)

## Phase 10: Pages — brands

- [x] 10.1 Create `apps/web/app/(site)/brands/page.tsx` (SearchInput + paginated BrandCard list, try/catch on fetcher to surface empty state on 422), `apps/web/app/(site)/brands/[slug]/page.tsx` (editorial header + paginated FragranceCard grid), `apps/web/app/(site)/brands/[slug]/loading.tsx`. URL `?q=` reads from `searchParams`. (~25 min)

## Phase 11: Pages — perfumers

- [x] 11.1 Create `apps/web/app/(site)/perfumers/page.tsx`, `apps/web/app/(site)/perfumers/[slug]/page.tsx`, `apps/web/app/(site)/perfumers/[slug]/loading.tsx`. Mirror brands shape with `getPerfumers` / `getPerfumerBySlug` and `PerfumerCard`. Header copy "Perfumer" / "Perfumers". (~20 min)

## Phase 12: Pages — articles

- [x] 12.1 Create `apps/web/app/(site)/articles/page.tsx` (list of `ArticleCard`, ordered by published_at DESC from API, paginated), `apps/web/app/(site)/articles/[slug]/page.tsx` (title + date + `<ArticleBody body={...}>` per `design.md`), `apps/web/app/(site)/articles/[slug]/loading.tsx`. `generateMetadata` description = `body?.slice(0, 160) ?? title`. (~25 min)

## Phase 13: Home + sitemap

- [x] 13.1 Edit `apps/web/app/(site)/page.tsx` per `design.md §"Home page modifications"`: mood tile hrefs flip from `/fragrances?accord=<slug>` to `/accords/<slug>`; replace journal placeholder with active teaser fetching `getAllArticles({ limit: 3 })` in a try/catch (warn on failure, render empty grid), render 3 `ArticleCard`s + "All essays →" link. (~15 min)
- [x] 13.2 Edit `apps/web/app/sitemap.ts` per `design.md §"Sitemap update"`: add 5 resource enumerations (notes via tree-walk, accords, brands, perfumers, articles). Each loop bounded by `MAX_PAGES = 200`. Wrap each loop in try/catch with `console.warn` on failure. (~20 min)

## Phase 14: Tests

- [x] 14.1 Vitest unit tests: `NoteTree` (render branches collapsed; click expands; leaf is plain Link), `AccordCard` / `BrandCard` / `PerfumerCard` / `ArticleCard` (snapshot href + label), `SearchInput` (mock `useRouter`/`useSearchParams`; type "abc"; assert `router.replace` called once after 300ms with `?q=abc`). Place under `apps/web/__tests__/components/`. (~30 min)
- [x] 14.2 Vitest sanitize negative test for `ArticleBody`: feed markdown containing `<script>alert(1)</script>`, `<iframe src=...>`, `<a onclick="x" href="x">`, `<p style="color:red">`. Assert `container.innerHTML` contains NONE of: `<script`, `<iframe`, ` onclick=`, ` style=`. Also assert external link gets `rel="noopener noreferrer"` + `target="_blank"`. Also positive test: GFM table + fenced code render as `<table>` / `<pre><code>`. (~20 min)
- [x] 14.3 Playwright manual-trigger smoke specs (per route family): `/notes`, `/notes/[seed-slug]`, `/notes/bogus → 404`, `/accords`, `/accords/woody`, `/brands`, `/brands?q=cha`, `/brands/[seed-slug]`, `/perfumers`, `/perfumers/[seed-slug]`, `/articles`, `/articles/[seed-slug]`. Each: assert status 200 (or 404 for bogus) and expected heading/element. Skip if seed dataset lacks an article body — flag in self-check. (~30 min)

## Phase 15: Self-check

- [x] 15.1 Run `pnpm --filter web build` — paste last 10 lines into apply log. Must succeed with no errors and no `react-markdown` ESM resolution warnings. (~5 min)
- [x] 15.2 Run `pnpm --filter web vitest run` + `pnpm --filter web exec tsc --noEmit` + `pnpm --filter web lint` — paste last 10 lines of EACH into apply log. All three must pass. (~10 min)
- [x] 15.3 ADR coverage verification — grep + snapshot evidence per ADR (0041 markdown stack imports in ArticleBody; 0042 SANITIZE_SCHEMA exported and excludes script/iframe/style/on*; 0043 ExternalAnchor in components prop; 0044 NAV imported in Header+MobileMenu; 0045 revalidate values match table in 10 fetchers/pages; 0046 every getXBySlug calls notFound on 404; 0047 ACCORD_COPY has 6 keys; 0048 SearchInput debounce=300ms; 0049 transpilePackages in next.config.ts). Output a 9-row PASS/FAIL table in apply log. (~15 min)
