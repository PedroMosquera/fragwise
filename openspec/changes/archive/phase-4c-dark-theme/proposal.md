# Proposal: Phase 4c — Dark Theme

## Intent

Lift the launch-blocking light-only constraint from P4a/P4b and ship a
hand-tuned dark theme behind a 3-state toggle. P4a deferred dark mode
(ADR-0033, ADR-0037); shadcn primitives already carry `dark:` variant
classes that are inert today because Tailwind v4 has not been told that
`.dark` is the dark-mode selector and `next-themes` is in `forcedTheme`
mode. 4c flips that switch, authors a dark token block, exposes the
toggle, and adapts the one component (`ImageFallback`) that hard-codes
a light-only lightness.

## Scope

### In Scope
- Tailwind v4 `@custom-variant dark (&:where(.dark, .dark *));` in
  `app/globals.css` — without it all `dark:` utilities silently no-op
  (exploration "Library Reality / Tailwind v4")
- `.dark` token block in `styles/tokens.css` with hand-tuned oklch
  values for all existing `--color-*` tokens plus `--fallback-l`
- Drop `color-scheme: light;` from `tokens.css` (Q5)
- `viewport.colorScheme` → `"light dark"` in `app/layout.tsx` (Q5)
- `next-themes` config: drop `forcedTheme="light"`,
  `enableSystem={true}`, keep `defaultTheme="light"` (Q4)
- New client island `components/site/ThemeToggle.tsx`: 3-state cycle
  light → dark → system → light, lucide Sun/Moon/Monitor,
  state-reflective `aria-label` (Q3)
- Insert `<ThemeToggle />` into `Header.tsx` (between disabled search
  and `MobileMenu`) and into `MobileMenu.tsx`
- `ImageFallback.tsx` CSS-variable refactor: `oklch(var(--fallback-l)
  0.06 hue)` with `--fallback-l: 0.78` (light) / `0.45` (dark);
  foreground glyph swap via paired CSS variable (Q6, Option A)
- Verify `components/ui/sonner.tsx` `--popover` token alias works in
  dark; patch to `--color-popover` if not (Q8)
- Vitest: `ThemeToggle` cycle + aria assertions; `ImageFallback`
  resolves different `--fallback-l` per theme
- Playwright `e2e/color-mode.spec.ts`: `emulateMedia` dark + toggle
  cycling asserts `<html>` class; keyboard reaches toggle (Q10)
- `@axe-core/playwright` contrast pass on `/` in dark mode (Q10)
- Spec deltas per Q11 (REPLACED + ADDED)

### Out of Scope
- `@tailwindcss/typography` install (`prose-stone` no-op stays; Q9)
- `defaultTheme="system"` migration (post-launch patch; Q4)
- Dark-mode catalog imagery (only `ImageFallback` adapts; no real
  fragrance images yet)
- Per-component visual snapshot regression (axe + functional only)

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `design-system`: REPLACED `Light Theme Tokens And Display Fonts` →
  `Light And Dark Theme Tokens` (covers both palettes + Tailwind v4
  `@custom-variant dark`); ADDED `Tailwind v4 Dark Variant Configured
  For Class Selector`
- `web-app`: REPLACED `Site Layout` (theme toggle in Header +
  MobileMenu); REPLACED `Theme Provider Wired With Light-Only Mode` →
  `Theme Provider Supports Light, Dark, And System`; ADDED `Theme
  Toggle Cycles 3-State`; ADDED `System Theme Respected`; ADDED
  `First-Paint Theme Stability`

## Approach

Tokens-first, mechanical (exploration "Approaches Considered" #1).
The `frontend-design` skill is invoked in `sdd-design` (Q12, mirrors
ADR-0033) to lock the dark oklch palette, accent chroma posture, and
`ImageFallback` dark L value before any code lands. Apply phase then
re-authors `--color-*` tokens under `.dark`, declares the Tailwind v4
custom variant, drops `forcedTheme`, ships the toggle island, and
flips `ImageFallback` to a CSS-variable lightness. No component
rewrites required — shadcn primitives already carry `dark:` classes.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/web/styles/tokens.css` | Modified | Add `.dark` block, `--fallback-l` var; drop `color-scheme: light` |
| `apps/web/app/globals.css` | Modified | `@custom-variant dark` declaration |
| `apps/web/app/layout.tsx` | Modified | Drop `forcedTheme`; `enableSystem={true}`; `viewport.colorScheme="light dark"` |
| `apps/web/components/site/Header.tsx` | Modified | Insert `<ThemeToggle />` |
| `apps/web/components/site/MobileMenu.tsx` | Modified | Insert `<ThemeToggle />` |
| `apps/web/components/site/ThemeToggle.tsx` | New | Client island, 3-state cycle |
| `apps/web/components/catalog/ImageFallback.tsx` | Modified | CSS-variable L refactor + foreground swap |
| `apps/web/components/ui/sonner.tsx` | Verify | Patch token alias if dark breaks |
| `apps/web/__tests__/components/ThemeToggle.test.tsx` | New | Vitest cycle + aria |
| `apps/web/e2e/color-mode.spec.ts` | New | Playwright + axe-on-home dark |
| `openspec/specs/design-system/spec.md` | Delta | Per Q11 |
| `openspec/specs/web-app/spec.md` | Delta | Per Q11 |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tailwind v4 `@custom-variant dark` missing → `dark:` utilities inert | Med | Apply verifies; one `dark:` smoke check on shadcn Button |
| Editorial aesthetic drift ("AI-default-dark slop") | Med | `frontend-design` skill in `sdd-design` (Q12) |
| First-paint flash after dropping `forcedTheme` | Low | Playwright spec asserts no FOUC on `defaultTheme="light"` first visit |
| `ImageFallback` dark contrast fails WCAG AA | Med | Design pass picks L; apply runs axe on dark `/` |
| Sonner `--popover` alias breaks in dark (Q8) | Low | Apply triggers a real toast in dark; patch to `--color-popover` if needed |
| Glossary popover bg matches page bg in dark → invisible | Low | Design pass enforces "popover slightly lighter than page" elevation |
| Palette drift across ~14 tokens | Med | Design pass produces side-by-side table; verify diffs the set |

## Rollback Plan

- **Pre-merge**: `git reset` — change is isolated to listed paths.
- **Post-merge / pre-deploy**: revert the merge commit; no data
  migrations; no DB writes.
- **Post-deploy**: theme toggle is purely additive. Revert if needed.
  User-visible state is per-browser via `next-themes` localStorage
  (default key `"theme"`); no server-side state to clean up.

## Dependencies

- `@axe-core/playwright` (new dev dep) for the dark contrast smoke
- `lucide-react` (already installed) for Sun/Moon/Monitor icons
- `frontend-design` skill round-trip in `sdd-design`

## Success Criteria

- [ ] All `dark:` utilities on shadcn primitives fire when `<html>`
      has `.dark`
- [ ] `ThemeToggle` cycles light → dark → system → light; aria-label
      reflects current state
- [ ] System theme honored when user picks `system`
      (`prefers-color-scheme` resolves correctly)
- [ ] No FOUC on first visit with `defaultTheme="light"`
- [ ] axe-core reports zero contrast violations on `/` in dark mode
- [ ] `ImageFallback` panel + glyph pass WCAG AA in both themes
- [ ] Sonner toast renders correctly when triggered in dark mode
- [ ] Vitest + Playwright suites green
- [ ] `design-system` and `web-app` deltas archived into canonical
      specs after `sdd-verify`
