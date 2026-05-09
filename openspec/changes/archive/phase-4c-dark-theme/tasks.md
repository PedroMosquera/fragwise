# Tasks: Phase 4c — Dark Theme

## Apply discipline (read first)

Per orchestrator retrospective on subagent quality:
1. **Smoke-import every new module** (ThemeToggle) before marking the task done. Use `pnpm --filter web exec tsx --eval "import('./components/site/ThemeToggle.tsx')"`.
2. **Run `pnpm --filter web build`** after task 6 (ImageFallback refactor) and before tests. If build fails, fix BEFORE proceeding.
3. **Critical Tailwind v4 gotcha**: WITHOUT the `@custom-variant dark` declaration in globals.css, all `dark:` utility classes silently no-op. After task 2.2, smoke-test by toggling `<html class="dark">` in dev tools and confirming a single `dark:bg-card` utility resolves.
4. **AA contrast validation**: Run `axe` on home page in dark mode (Playwright fixture). Verify ImageFallback `--fallback-l = 0.42` produces ≥3:1 contrast against ivory glyph for ALL 6 hue bands. If hue 200 (cyan) fails, drop to 0.40 per design's permitted range.
5. **FOUC validation**: Take a screenshot at first navigation; assert background color is the light token (no transparent/white flash).
6. **Sonner smoke**: trigger a real toast (e.g., from a dev keybinding) in dark mode; verify the popover bg + border resolve correctly.
7. **Output reporting discipline**: paste last 10 lines of `pnpm --filter web build`, `pnpm --filter web vitest run`, `pnpm --filter web exec tsc --noEmit`, `pnpm --filter web lint`.

## Phase 1: Pre-flight

- [x] 1.1 Confirm working branch is clean and `phase-4b` is archived; verify `apps/web/styles/tokens.css`, `apps/web/app/globals.css`, `apps/web/app/layout.tsx`, `apps/web/components/site/Header.tsx`, `apps/web/components/site/MobileMenu.tsx`, `apps/web/components/catalog/ImageFallback.tsx`, `apps/web/components/ui/sonner.tsx` exist at their P4b state. **Verify with**: `git status` clean + `ls openspec/changes/archived/phase-4b-*` returns directory. (~5 min)

## Phase 2: Tokens + globals

- [x] 2.1 Update `apps/web/styles/tokens.css` per `design.md §"tokens.css full content"`. Add `:root.dark` block with all 19 dark `--color-*` tokens + `--fallback-l: 0.42` + `--fallback-fg: oklch(0.96 0.005 90)`. Add `--fallback-l: 0.78` and `--fallback-fg: oklch(0.21 0.025 270)` to `:root`. Drop `color-scheme: light;` from `:root`. **Verify with**: `grep ":root.dark" apps/web/styles/tokens.css` returns the new block AND `grep "color-scheme:" apps/web/styles/tokens.css` returns nothing. (~10 min)
- [x] 2.2 Update `apps/web/app/globals.css`: insert `@custom-variant dark (&:where(.dark, .dark *));` immediately after `@import "tailwindcss";` and before the tokens import. **Verify with**: `grep "@custom-variant dark" apps/web/app/globals.css` returns the line; manual smoke — toggle `<html class="dark">` in dev tools and confirm `dark:bg-card` resolves on a sample element. (~5 min)

## Phase 3: Layout config

- [x] 3.1 Update `apps/web/app/layout.tsx` per `design.md §"app/layout.tsx diff"`: drop `forcedTheme="light"`, set `enableSystem={true}`, change `viewport.colorScheme` from `"light"` to `"light dark"`. Keep `defaultTheme="light"` and `disableTransitionOnChange`. **Verify with**: `grep -E "forcedTheme|colorScheme|enableSystem" apps/web/app/layout.tsx` shows only `enableSystem={true}` and `colorScheme: "light dark"`. (~5 min)

## Phase 4: ThemeToggle component

- [x] 4.1 Create `apps/web/components/site/ThemeToggle.tsx` per `design.md §"ThemeToggle.tsx (new, full content)"`: `"use client"` island, 3-state cycle (light → dark → system → light), lucide `Sun`/`Moon`/`Monitor`, state-reflective `aria-label`, mount-guard via `useState(false)` + `useEffect`. **Verify with**: `pnpm --filter web exec tsx --eval "import('./components/site/ThemeToggle.tsx')"` succeeds and `pnpm --filter web exec tsc --noEmit` passes. (~15 min)

## Phase 5: Header + MobileMenu integration

- [x] 5.1 Update `apps/web/components/site/Header.tsx` and `apps/web/components/site/MobileMenu.tsx` per `design.md §"Header.tsx diff"` and `§"MobileMenu.tsx diff"`. Header: insert `<ThemeToggle />` after the disabled search input in the desktop cluster AND add a separate `<md` cluster wrapping `<ThemeToggle />` before `<MobileMenu />`. MobileMenu: insert `<ThemeToggle />` block (with "Theme" label + border-top divider) after the nav list inside `<SheetContent>`. **Verify with**: `grep -c "ThemeToggle" apps/web/components/site/Header.tsx` returns 3 (1 import + 2 usages); `grep -c "ThemeToggle" apps/web/components/site/MobileMenu.tsx` returns 2. (~10 min)

## Phase 6: ImageFallback refactor

- [x] 6.1 Rewrite `apps/web/components/catalog/ImageFallback.tsx` per `design.md §"ImageFallback.tsx (full rewrite)"`: emit `--fallback-h: <degree>` inline; `backgroundColor: "oklch(var(--fallback-l) 0.06 var(--fallback-h))"`; glyph `color: "var(--fallback-fg)"`. Keep the `BANDS` array and `panelHue()` server-side hash logic. **Verify with**: `pnpm --filter web build` succeeds (paste last 10 lines); `grep "var(--fallback-l)" apps/web/components/catalog/ImageFallback.tsx` returns the literal. (~15 min)

## Phase 7: Sonner patch

- [x] 7.1 Update `apps/web/components/ui/sonner.tsx` per `design.md §"Sonner verification"` patch diff: rename `var(--popover)` → `var(--color-popover)`, `var(--popover-foreground)` → `var(--color-popover-foreground)`, `var(--border)` → `var(--color-border)`, `var(--radius)` → `var(--radius-md)` in the `style` prop. **Verify with**: `grep -E "var\\(--popover\\)|var\\(--border\\)|var\\(--radius\\)" apps/web/components/ui/sonner.tsx` returns nothing; manual — fire a real toast in dev (dark mode) and confirm popover bg + border + radius resolve. (~5 min)

## Phase 8: Tests

- [x] 8.1 Create `apps/web/__tests__/components/ThemeToggle.test.tsx` (Vitest): mock `next-themes` `useTheme`; render; assert initial `aria-label` for light; click 3×; assert `setTheme` called with `dark`, then `system`, then `light` in order; assert `aria-label` mutates on each render to reflect the mocked theme. **Verify with**: `pnpm --filter web vitest run __tests__/components/ThemeToggle.test.tsx` is green. (~20 min)
- [x] 8.2 Create `apps/web/e2e/color-mode.spec.ts` (Playwright + axe): (a) cold visit `/`, assert `<html class="light">`, screenshot first paint and assert background ≠ transparent/white (FOUC gate); (b) click toggle 3×, assert `<html>` class transitions light→dark→system→light; (c) `page.emulateMedia({ colorScheme: 'dark' })`, set theme to system, assert `<html class="dark">`, switch to light emulation, assert `<html class="light">`; (d) tab from search input, assert ThemeToggle is the next focusable; (e) `@axe-core/playwright` scan on `/` in dark mode — assert zero color-contrast violations. Add `@axe-core/playwright` to `apps/web/package.json` devDependencies. **Verify with**: `pnpm --filter web exec playwright test e2e/color-mode.spec.ts` is green. (~30 min)

## Phase 9: Self-check

- [x] 9.1 Run `pnpm --filter web build` from repo root; paste last 10 lines of output into the apply summary. Build MUST succeed (zero errors). If it fails, fix BEFORE proceeding to 9.2. (~5 min)
- [x] 9.2 Run in sequence and paste last 10 lines of each into apply summary: `pnpm --filter web vitest run`, `pnpm --filter web exec tsc --noEmit`, `pnpm --filter web lint`. All three MUST be green. (~10 min)
- [x] 9.3 Run axe contrast pass on `/` in dark mode via the Playwright spec from 8.2; verify ImageFallback `--fallback-l = 0.42` glyph contrast passes WCAG AA on ALL 6 hue bands (`[25, 35, 45, 70, 200, 280]`). If hue 200 (cyan) fails, drop `--fallback-l` to `0.40` in `tokens.css :root.dark` and re-run; record the final value in the apply summary. **Verify with**: axe report shows zero color-contrast violations on the dark home page. (~10 min)
