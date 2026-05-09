# Exploration: Phase 4c — Dark Theme

> **Status**: exploration only. No code, no design decisions ratified.
> Surfaces unknowns, risks, and trade-offs. The orchestrator returns
> with a list of decisions the user MUST ratify before `sdd-propose`.

## Current State (post-4b)

`apps/web/` is feature-complete in **light mode only**. P4a locked the
editorial-perfumery aesthetic (ADR-0033, ADR-0037); P4b added taxonomy
pages and the `NAV` feature-flag map but explicitly deferred dark mode
to 4c (proposal 4b → "Dark theme deferred to phase 4c per
D-DarkTheme; ADR-0037"). No follow-up decisions about palette values,
toggle UX, or system-detection behavior have been recorded yet.

What's already in place that 4c can lean on:

- `apps/web/styles/tokens.css` — light-only oklch token block at
  `:root`. `color-scheme: light` declared.
- `apps/web/app/globals.css` — `@import "tailwindcss"` then
  `@import "../styles/tokens.css"`; Tailwind v4 `@theme inline` block
  bridges `--color-*` tokens into utilities. **No `@custom-variant
  dark` and no `.dark { … }` block exist.**
- `apps/web/app/layout.tsx` — `<html lang="en" suppressHydrationWarning>`
  + `<ThemeProvider attribute="class" defaultTheme="light"
  forcedTheme="light" enableSystem={false}
  disableTransitionOnChange>`. `viewport.colorScheme = "light"`.
- `apps/web/components/theme-provider.tsx` — passthrough wrapper around
  `next-themes`'s `<ThemeProvider>`. Already client-component; nothing
  to change there.
- `apps/web/components/site/Header.tsx` — server component. The right-
  side cluster has the disabled search input slot only. **There is no
  scaffolded toggle position today** (the brief mentions a "scaffold
  position" but the file's current source contains only the search
  input followed by `<MobileMenu>`).
- `apps/web/components/site/MobileMenu.tsx` — Radix Sheet drawer; lists
  NAV items only. No theme controls today.
- `apps/web/components/ui/sonner.tsx` — already calls `useTheme()` from
  `next-themes` and forwards `theme` to the Sonner Toaster. Will start
  flipping correctly the moment `forcedTheme` is dropped — no change
  needed in this file.
- `apps/web/components/catalog/ImageFallback.tsx` — server-component
  fallback panel using `oklch(0.78 0.06 <hue>)` for background and
  `var(--color-foreground)` for the dark ink glyph. The L=0.78 lightness
  is an intentional WCAG AA pivot for **dark ink on light pastel**;
  inverting the page background to dark leaves a glaring pastel chip
  with deep-ink ink that will lose contrast.
- `apps/web/components/editorial/ArticleBody.tsx` — uses
  `className="prose prose-stone max-w-prose"`. **`@tailwindcss/typography`
  is NOT installed**, so `prose` and `prose-stone` are silently no-ops
  today. Body text rendering relies entirely on globals + Tailwind
  default heading styles (no special-case dark mode work needed for
  ArticleBody itself, *unless* we install typography in 4c, which I do
  not recommend mixing in here).
- shadcn primitives shipped during 0b/4a contain **`dark:` variant
  classes already** (Button, Tabs, Badge, Input, Select, DropdownMenu,
  …). They are inert today because:
  1. The `.dark` class is never applied to `<html>` (forcedTheme), AND
  2. Tailwind v4 has not been told that `.dark` is the dark-mode
     selector via `@custom-variant dark`. Without that declaration,
     `dark:` utilities only fire on `prefers-color-scheme: dark` —
     which does nothing for our class strategy.
- ADR sequence: last issued is **ADR-0049** (P4b ESM transpile).
  Phase 4c starts at **ADR-0050**.
- `apps/web/.size-limit.json` — single budget: 600 KB gzipped for all
  static client chunks. Dark-mode work is CSS-only on the critical path
  (toggle component is the only new client JS) and should remain well
  under budget.

## Affected Areas

- `apps/web/styles/tokens.css` — add a dark theme block; rework `color-
  scheme`.
- `apps/web/app/globals.css` — declare `@custom-variant dark
  (&:where(.dark, .dark *));` so Tailwind v4 emits dark utilities for
  the class strategy. Without this, the existing shadcn `dark:` classes
  stay inert.
- `apps/web/app/layout.tsx` — drop `forcedTheme`; flip
  `enableSystem` to `true`; relax `viewport.colorScheme` to
  `"light dark"` (or remove the meta and rely on `next-themes`'s own
  `enableColorScheme`).
- `apps/web/components/site/Header.tsx` — add the `<ThemeToggle />`
  slot. (Note: this is a server component today. The toggle button is
  client-only; we can either render a small `"use client"` toggle as a
  child or extract a tiny client island. Keeping `Header` a server
  component and dropping a client child is the cleanest path.)
- `apps/web/components/site/MobileMenu.tsx` — add the same toggle as
  the last item inside the sheet.
- `apps/web/components/catalog/ImageFallback.tsx` — revisit the panel
  lightness for dark mode (the L=0.78 pastel + dark-ink glyph
  combination is glaring and loses uniformity when sitting on a near-
  black page background).
- New file: `apps/web/components/site/ThemeToggle.tsx` (client) —
  the actual toggle button.
- `apps/web/__tests__/` — add a vitest render test for the toggle
  (verify cycle order, aria-label).
- `apps/web/e2e/` — add a Playwright color-scheme smoke
  (`page.emulateMedia({ colorScheme: 'dark' })` + screenshot, plus
  toggle-click assertions).
- `openspec/specs/design-system/spec.md` — needs a DELTA: dark theme
  tokens; `@custom-variant dark` declaration; the no-dark-tokens
  scenario from 4a is now obsolete (will be REPLACED, not removed
  silently — see Open Question Q2).
- `openspec/specs/web-app/spec.md` — needs a DELTA: theme toggle
  requirement; system theme respected; first-paint stability (no
  flash); `viewport.colorScheme` updated.

## Library Reality (Context7-verified)

### `next-themes` 0.4.x

- `attribute="class"` writes the active theme name (`light`, `dark`,
  or `system`-resolved value) directly to `<html>` as a class. With
  `value` map omitted, the class is literally `dark` — which matches
  Tailwind's expected selector.
- `enableSystem={true}` adds `system` to the `themes` array and
  resolves it via `prefers-color-scheme: dark`. `useTheme().theme`
  returns `'system'` while `useTheme().resolvedTheme` returns the
  concrete `'light'` or `'dark'`.
- `defaultTheme` is the value used **before** any localStorage entry
  exists. Setting `defaultTheme="light"` with `enableSystem={true}`
  means: first-ever visitor sees light, then can opt into system; once
  they pick, the choice persists in localStorage under the
  `next-themes`-managed key (default `"theme"`).
- `forcedTheme` overrides everything (no toggle, no localStorage).
  Removing it is the entire mechanism by which 4c "turns on" dark.
- `enableColorScheme` (default `true`) writes the CSS `color-scheme`
  property on `<html>` automatically based on the active theme. **This
  collides with our hand-authored `color-scheme: light;` in
  `tokens.css`** — `next-themes`'s inline style on `<html>` will win
  but the CSS rule is dead code that needs cleaning up.
- `useTheme` is a client-only hook (uses React Context). It cannot be
  called inside React Server Components. Confirmed pattern: the
  toggle must be a `"use client"` island. Header itself stays RSC.
- FOUC prevention: the `<ThemeProvider>` injects an inline script tag
  in `<head>` that synchronously reads localStorage and writes the
  `class`/`data-theme` attribute **before paint**. `<html
  suppressHydrationWarning>` is already set in our layout. This is the
  standard, well-tested path; no observed regression in Next 16.

### Tailwind v4

- The `dark:` variant defaults to `prefers-color-scheme: dark`.
  Switching it to a class selector requires
  `@custom-variant dark (&:where(.dark, .dark *));` somewhere in the
  CSS (top-level, after the `@import "tailwindcss";` line).
- We can author the dark token block as either:
  - `:root.dark { … }` (selector match identical to Tailwind's variant)
  - `.dark { --color-background: …; }` (also fine; `.dark` lives on
    `<html>`).
- The existing `@theme inline` block does NOT need duplication: it
  references `var(--color-background)` etc., so as long as the
  `--color-*` variables are redefined under `.dark`, all utilities
  flip automatically.
- Tailwind v4 also supports `light-dark()` CSS function in `@theme`
  blocks, but that's a different strategy (relies on
  `prefers-color-scheme`) and would conflict with our class-based
  toggle. Stay with `@custom-variant dark` + class flip.

### Next.js 16 viewport

- `viewport.colorScheme` accepts `'normal' | 'light' | 'dark' |
  'light dark' | 'only light'`. With `next-themes` writing
  `color-scheme` on `<html>` already (via `enableColorScheme`), the
  `<meta name="color-scheme">` tag is mostly a hint to UAs before
  hydration. `"light dark"` is the safe value: tells the browser our
  styles cover both schemes; the JS-injected inline style on `<html>`
  refines this to the active theme before paint.

## Open Questions / Unknowns the User MUST Decide

These are gates before `sdd-propose` runs.

### Q1 — Palette derivation strategy

| Option | Description | Pros | Cons | Effort |
|---|---|---|---|---|
| A | Hand-tuned dark oklch palette (recommend) | Preserves editorial-perfumery feel; matches ADR-0033's "no AI-slop dark" guardrail | Requires a frontend-design pass | Medium |
| B | Naive HSL/oklch lightness invert | Cheap, mechanical | Will look generic; chroma at high L doesn't translate at low L | Low |
| C | `light-dark()` with auto-derived deltas | Single source-of-truth | Forces media-query strategy; conflicts with class toggle | N/A — rejected |

**Recommendation**: A. Mirrors P4a's pattern of invoking the
`frontend-design` skill during `sdd-design` to lock the palette
(ADR-0033 was authored that way). Without a design pass, dark-mode
fragwise will feel "AI-default-dark."

### Q2 — Sepia accent in dark mode

Light theme uses warm sepia accent (`oklch(0.62 0.12 30)` for `--color-
accent`, `oklch(0.30 0.05 35)` for `--color-primary`). In dark mode the
choice is:

- **Keep warm**, lower chroma (recommend: `oklch(0.72 0.08 30)` ish)
  → preserves brand identity
- Shift to cool (blue/green) → modern but breaks brand cohesion
- Boost chroma to compensate for darker surround → risk of looking
  neon-y

**Recommendation**: keep warm, lower chroma; defer exact values to
`frontend-design` skill in `sdd-design`.

### Q3 — Toggle cycle: 2-state vs 3-state

- **3-state (light → dark → system → light)**: power-user friendly;
  matches `next-themes`'s `themes: ['light','dark','system']` model;
  three icons (Sun/Moon/Monitor from lucide).
- **2-state (light ↔ dark)**: simpler; loses system-following.

**Recommendation**: 3-state. The cost is one extra icon; the user-
behavioral payoff (respect OS auto-switch on macOS Sequoia / iOS) is
material for an editorial site read at all hours.

### Q4 — Default theme on first visit

- `defaultTheme="light"`: first-ever paint is always ivory; user can
  opt in. Predictable for marketing screenshots; loses OS-respect on
  the very first pageview.
- `defaultTheme="system"`: first-ever paint resolves to the OS
  preference. More respectful; but a user on dark OS sees a not-yet-
  fully-tested dark UI on landing.

**Recommendation**: ratify `defaultTheme="light"` for the launch (P4c
ships, dark goes through QA in production, first-ever visitors get
the canonical light look). Switch to `system` in a follow-up patch
once dark has been observed in the wild.

### Q5 — `viewport.colorScheme` final value

- `"light"` (today) — wrong once dark exists; OS dark users see dark
  scrollbars on light page until JS hydrates. Bad.
- `"light dark"` — declares both; UA picks based on OS; once
  next-themes inline-style fires, `<html style="color-scheme: …">`
  takes over.
- Remove the meta entirely — fall back to next-themes's runtime
  `color-scheme` write.

**Recommendation**: `"light dark"` in `viewport`. Belt-and-suspenders
for pre-hydration paint. Also drop the `color-scheme: light;`
declaration from `tokens.css` (it conflicts with next-themes's runtime
write and is now obsolete anyway).

### Q6 — ImageFallback dark-mode strategy

The slug-hashed pastel panel (`oklch(0.78 0.06 H)`) with deep-ink
glyph (`var(--color-foreground)`) is a deliberate light-theme device.
Three options:

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | CSS variable for the L value: `--fallback-l: 0.78` light, `0.45` dark; component reads `oklch(var(--fallback-l) 0.06 var(--fallback-h))` | RSC-safe; no client JS; per-instance hue still computed from slug; foreground flips via existing `--color-foreground` token | Requires emitting `--fallback-h` as an inline style (already doing inline `backgroundColor`; trivial swap) |
| B | Use `useTheme()` and compute the inline style client-side | Trivial logic | Forces ImageFallback to become a client component; ALL usage sites then become client subtrees; breaks RSC; bigger bundle |
| C | Two stacked elements, light visible normally, dark visible under `.dark` ancestor | Pure CSS | DOM bloat (every fallback adds two divs); accessibility considerations |
| D | Drop the pastel panel in dark mode entirely; use a single neutral dark-card surface | Cohesive dark feel | Loses the slug-deterministic identity that makes catalog cards distinguishable in light theme |

**Recommendation**: **Option A**. Author `panelOklch()` to emit two
CSS custom properties (`--fallback-bg-l` and `--fallback-h`) inline,
then use a static `oklch(var(--fallback-bg-l) 0.06 var(--fallback-h))`
in the panel. Override `--fallback-bg-l` to ~`0.32–0.40` (TBD by
frontend-design pass) under `.dark`. **Foreground glyph** in dark
mode: do NOT keep `var(--color-foreground)` at the same value — when
panel L is 0.32, deep-ink (oklch 0.21) won't pass AA. Instead, swap
the glyph foreground to a high-L token (`oklch(0.96 0.005 90)`) under
`.dark`. Either via a paired CSS variable or a `dark:` utility on the
glyph.

### Q7 — Accord blurb popovers (`Glossary`) in dark

Popover background today uses `--color-popover` which auto-flips with
dark tokens. But the **dotted underline accent border** is on
`--color-accent` — see Q2 for the dark-mode accent decision. Risk: in
dark mode the dotted underline may either disappear (low contrast) or
look neon (high chroma). Frontend-design pass should validate.

### Q8 — Sonner toaster

Already wired with `useTheme()` + `theme={theme as ToasterProps[…]}`.
With `enableSystem=true` and `theme === 'system'`, Sonner respects OS.
**No code change needed** in `sonner.tsx`; just drop `forcedTheme` and
the toaster starts honoring the choice.

### Q9 — `prose` content under dark

`ArticleBody` uses `prose prose-stone` but `@tailwindcss/typography`
isn't installed → these classes are no-ops today. Body text inherits
from `:root` color/font on `<html>`. Once the `--color-foreground`
flips under `.dark`, all body text follows. **No change needed**;
explicitly note in design that we are NOT installing typography in 4c.

### Q10 — Smoke testing posture

Two layers, no gold-plating:

- **Vitest**: render-test the new `<ThemeToggle />` to verify cycle
  order and aria-labels. Vitest with jsdom cannot test computed-style
  contrast or actual color rendering; do not attempt that there.
- **Playwright**: one new spec, `e2e/color-mode.spec.ts`. Asserts:
  (1) `prefers-color-scheme: dark` emulation results in `.dark` on
  `<html>` after hydration when user chose `system`; (2) clicking the
  toggle cycles `light → dark → system → light` and updates the html
  class accordingly; (3) one screenshot in each mode (visual snapshot
  is optional — adds maintenance cost; recommend leaving snapshots
  off and only asserting class state + visible aria-label).

**Open**: do we add an axe-core run? `@axe-core/playwright` would let
us assert WCAG AA contrast in both modes. Cost: one new dev dep, ~1
minute of CI on the manual workflow_dispatch. **Recommendation**:
include the axe assertion *only* on the home page in dark mode. If
that passes, the rest of the surfaces inherit the same tokens. Avoid
auditing every route — diminishing returns.

### Q11 — Spec delta strategy

P4a's design-system spec contains "Dark theme tokens MUST NOT be
defined in Phase 4a" inside Requirement "CSS Token File With Light
Theme Variables", plus a scenario "Dark theme deliberately absent in
4a." Both are **directly contradicted** by 4c.

The `sdd-spec` step needs to:
- **REPLACE** that requirement with a new "CSS Token File With Light
  And Dark Theme Variables" requirement (use `## REPLACED Requirement:`
  + new `## ADDED Requirement:`, per OpenSpec convention) — flag this
  for `sdd-spec` so it knows it cannot just append.
- **REPLACE** the "Theme Provider Wired With Light-Only Mode"
  requirement with a "Theme Provider Supports Light, Dark, and System"
  requirement.
- **ADD** a "Theme Toggle Available in Header and Mobile Menu"
  requirement to `web-app`.
- **ADD** a "First-Paint Theme Stability" requirement to `web-app`
  (no FOUC; `<ThemeProvider>`'s pre-paint script handles this).
- **ADD** a "Tailwind v4 Dark Variant Configured For Class Selector"
  requirement to `design-system`.

### Q12 — Frontend-design skill invocation

P4a's design phase invoked `frontend-design` to lock the editorial-
perfumery palette and ADR-0033. Dark mode is a meaningful aesthetic
extension (not a mechanical port). The design phase for 4c **MUST**
invoke `frontend-design` again to:

- propose the dark oklch palette
- decide accent chroma posture
- propose the ImageFallback dark L value
- check border/card elevation for dark hierarchy

Without this, ADR-0050+ will be "any plausible value" rather than a
ratified one. Confirm with user whether to spend that round-trip; the
brief explicitly says yes.

## Approaches Considered (high-level)

1. **Tokens-first, mechanical (recommended)** — declare
   `@custom-variant dark`, add `.dark { --color-* }` block in
   `tokens.css` with hand-tuned oklch values from the design pass,
   add toggle island, drop `forcedTheme`, relax viewport, swap
   ImageFallback L via CSS variable. No component refactors required.
   Effort: **Low–Medium**, mostly token work and one new component.

2. **Component-by-component dark variants** — leave tokens alone,
   author `dark:` variants on every component manually. Effort:
   **High**, error-prone, defeats the purpose of having a token
   system. Rejected.

3. **Two CSS files, one per theme, swapped via `<link media>`** —
   exotic; brings extra request overhead and no upside over the
   `@custom-variant + .dark { … }` pattern. Rejected.

## Risks

- **Palette drift between light and dark**. With ~14 color tokens to
  re-author, easy to leave one as-is. Mitigation: design pass
  produces a side-by-side table; verification step diffs the token
  set.
- **First-paint flash (FOUC)**. The `next-themes` inline script must
  fire before paint. Already wired via `<ThemeProvider>`; risk is
  low *except* if a future `<head>` reorder pushes our `<style>` after
  body content. Mitigation: Playwright spec asserts no flash by
  capturing the very first paint with `colorScheme` emulation.
- **OS dark-preference users hit a 0.5-second flash on first visit**
  if `defaultTheme="light"`. Tradeoff explicitly accepted in Q4.
- **OkLCh perceptual quirks**. At constant chroma, hues are not
  perceptually equivalent across L bands. The `frontend-design` pass
  catches this; manual review on at least three hues recommended.
- **shadcn `dark:` class inertness today is hidden**. The fix for
  this is a single `@custom-variant dark` line, but missing it
  leaves the toggle visually a no-op for many components and is hard
  to debug — it'll look like everything is broken. Call this out
  explicitly in tasks.
- **`color-scheme: light` declaration in `tokens.css`** must be
  reworked or deleted. Otherwise it conflicts with next-themes's
  runtime write on `<html>`.
- **Sonner**'s style block uses `--popover`, `--popover-foreground`,
  `--border` (without the `--color-` prefix). Quick check:
  `apps/web/components/ui/sonner.tsx` references `var(--popover)` —
  this is **not a defined token in our system** (we use
  `--color-popover`). It might be relying on shadcn's built-in
  alias. If it is, the dark flip happens automatically; if it is
  not, dark Sonner toasts will look broken. Verification needed in
  the design phase. (Same concern applies to `var(--border)` and
  `var(--radius)` references.)
- **Glossary popover contrast** in dark. Solution: the popover bg
  token needs to be slightly lighter than the page bg in dark mode
  (matching the "card slightly lighter than page" pattern in light).
- **Editorial aesthetic preservation**. Dark editorial-perfumery is
  hard. Without the `frontend-design` pass, the result will be
  generic.
- **ImageFallback uniform contrast guarantee disappears in dark**.
  ADR-0036 promises uniform AA at L=0.78. A new ADR (ADR-005x) needs
  to extend that guarantee to the dark L value chosen in Q6.

## Trade-offs

- 3-state vs 2-state toggle (Q3) — recommend 3-state.
- Hand-tuned vs mechanical palette (Q1) — recommend hand-tuned.
- `defaultTheme="light"` vs `"system"` (Q4) — recommend `"light"` for
  launch.
- Axe-on-home only vs axe-on-every-route (Q10) — recommend home only.
- Visual snapshot in Playwright (Q10) — recommend NO snapshots; only
  class-state assertions.
- Install `@tailwindcss/typography` to fix `prose-stone` no-op (Q9) —
  **defer**: out of 4c scope; tracking in a follow-up patch.

## Splits Worth Considering

| Split | Scope | Recommendation |
|---|---|---|
| 4c-1: tokens + variant + provider + toggle | The meat | Keep together |
| 4c-2: ImageFallback dark L + accord blurb popover dark contrast pass | Polish | Keep together |

**Recommendation**: do NOT split. The change is small and tightly
coupled; splitting forces 4c-1 to ship in a half-broken state where
the toggle works but image fallbacks look glaring on dark surfaces.

## Decisions the User MUST Ratify Before `sdd-propose`

1. **Q1**: hand-tuned oklch palette via `frontend-design` pass — yes / no
2. **Q2**: dark accent stays warm sepia, lower chroma — yes / no
3. **Q3**: 3-state toggle (light → dark → system → light) — yes / no
4. **Q4**: `defaultTheme="light"` for launch (not `system`) — yes / no
5. **Q5**: `viewport.colorScheme = "light dark"`; drop `color-scheme:
   light;` from `tokens.css` — yes / no
6. **Q6**: ImageFallback dark mode via CSS-variable L swap (Option A,
   RSC-safe) — yes / no
7. **Q10**: Playwright color-mode spec + axe-on-home dark; no visual
   snapshots — yes / no
8. **Q11**: spec deltas use `## REPLACED Requirement:` for the two 4a
   light-only requirements — yes / no
9. **Q12**: invoke `frontend-design` skill in `sdd-design` phase — yes /
   no
10. **Split posture**: keep 4c as a single change — yes / no
11. **Out-of-scope acknowledgements**:
    - `@tailwindcss/typography` install (defer)
    - `defaultTheme="system"` migration (defer to post-launch patch)
    - Dark-mode catalog imagery (out of scope; ImageFallback only)

## Ready for Proposal

**Yes**, once Q1–Q12 above are ratified. The technical surface is
small (one new client island, one CSS variant declaration, one token
block, three layout-level prop changes). The aesthetic surface
requires `frontend-design`. The spec surface needs care with
REPLACED-requirement deltas.
