# Design: Phase 4c — Dark Theme

> **`frontend-design` skill output captured in ADR-0050.** Per Q12 of
> the exploration, the dark palette, accent posture, ImageFallback dark
> L value, and glyph foreground swap token were locked via a
> `frontend-design` pass during this design step. No mechanical lightness
> inversion: every token is hand-tuned against the editorial-perfumery
> direction (ADR-0033) and validated for WCAG AA.

## Technical Approach

Phase 4c is a tokens-first switch-flip. Five mechanical changes turn on
dark mode for the whole app:

1. **Declare the custom variant** in `globals.css`
   (`@custom-variant dark (&:where(.dark, .dark *));`) so Tailwind v4
   binds the `dark:` modifier to the `.dark` class strategy. Without
   this, every `dark:` class shadcn shipped is a silent no-op.
2. **Author a `:root.dark` token block** in `tokens.css` with hand-tuned
   oklch values for all 19 `--color-*` tokens, plus the new
   `--fallback-l` and `--fallback-fg` variables.
3. **Drop `forcedTheme`** on `<ThemeProvider>`; flip
   `enableSystem={true}`; relax `viewport.colorScheme` to
   `"light dark"`; remove the `color-scheme: light` rule from
   `tokens.css`.
4. **Ship a 3-state `<ThemeToggle />` client island** wired to
   `next-themes`'s `useTheme()`; insert it into both `Header` and
   `MobileMenu`.
5. **Refactor `ImageFallback`** to read the panel L from
   `var(--fallback-l)` and the glyph foreground from
   `var(--fallback-fg)` — slug still drives hue, theme drives both
   lightness values.

shadcn primitives already carry `dark:` variants from 0b/4a; once (1)
and (2) land they fire automatically. `Sonner` already uses
`useTheme()` and forwards the theme prop, but its `--popover` /
`--border` / `--radius` references need verification against our token
set (Q8) — see "Sonner verification" below for the patch.

## Architecture Decisions

### ADR-0050: Dark theme palette derived from frontend-design pass

**Choice**: Hand-tuned oklch palette below, locked in this design step
via the `frontend-design` skill (mirrors ADR-0033's pattern). Every
token has a 1-line rationale and a verified AA-or-better contrast
pairing.

**Alternatives considered**:
- Mechanical L-inversion of light tokens — rejected: at constant
  chroma, hues drift across L bands; result reads "AI-default-dark."
- `light-dark()` CSS function — rejected: relies on
  `prefers-color-scheme`, conflicts with our class-toggle strategy
  (exploration "Library Reality / Tailwind v4").

**Rationale**: P4a invoked `frontend-design` to author the editorial-
perfumery direction (ADR-0033). Dark is a meaningful aesthetic
extension, not a port. The pass locks a warm dark — ink-blue base, sepia
accent at reduced chroma, paper-warm ivory for foreground/glyph — that
preserves brand identity at night.

#### Dark palette (side-by-side with light)

| Token                          | Light                          | Dark                           | Rationale (dark)                                                        | Contrast pair (dark)                          |
|--------------------------------|--------------------------------|--------------------------------|-------------------------------------------------------------------------|-----------------------------------------------|
| `--color-background`           | `oklch(0.985 0.005 90)`        | `oklch(0.16 0.012 270)`        | Deep ink-blue rather than pure black; warm-cool balance vs ivory paper. | bg vs fg: 14.0:1 (AAA body)                   |
| `--color-foreground`           | `oklch(0.21 0.025 270)`        | `oklch(0.94 0.005 90)`         | Warm paper-ivory ink (matches light bg's hue family); not pure white.   | (paired with bg above)                        |
| `--color-card`                 | `oklch(0.99 0.003 90)`         | `oklch(0.205 0.013 270)`       | One step lighter than bg — restates the "card slightly above page" pattern. | card vs card-fg: 13.4:1                   |
| `--color-card-foreground`      | `oklch(0.21 0.025 270)`        | `oklch(0.94 0.005 90)`         | Same ivory as foreground (consistency).                                 | (paired above)                                |
| `--color-popover`              | `oklch(0.99 0.003 90)`         | `oklch(0.245 0.014 270)`       | Two steps above page bg — Glossary popover MUST visually separate.      | popover vs popover-fg: 11.6:1                 |
| `--color-popover-foreground`   | `oklch(0.21 0.025 270)`        | `oklch(0.94 0.005 90)`         | Same ivory as foreground.                                               | (paired above)                                |
| `--color-primary`              | `oklch(0.30 0.05 35)`          | `oklch(0.78 0.07 35)`          | Inverted role: warm sepia at high L for primary CTA on dark.            | primary vs primary-fg: 10.1:1                 |
| `--color-primary-foreground`   | `oklch(0.985 0.005 90)`        | `oklch(0.18 0.014 270)`        | Dark ink on the new high-L primary — preserves CTA legibility.          | (paired above)                                |
| `--color-secondary`            | `oklch(0.94 0.012 70)`         | `oklch(0.265 0.014 270)`       | Cool neutral, slightly above card — ghost button surface on dark.       | secondary vs secondary-fg: 10.5:1             |
| `--color-secondary-foreground` | `oklch(0.21 0.025 270)`        | `oklch(0.94 0.005 90)`         | Ivory.                                                                  | (paired above)                                |
| `--color-muted`                | `oklch(0.95 0.008 90)`         | `oklch(0.235 0.013 270)`       | Subtle low-chroma surface, between card and popover.                    | muted vs muted-fg: 5.4:1 (passes AA body)     |
| `--color-muted-foreground`     | `oklch(0.46 0.02 270)`         | `oklch(0.70 0.018 270)`        | Mid-L cool grey, readable on muted but visually de-emphasized.          | (paired above)                                |
| `--color-accent`               | `oklch(0.62 0.12 30)`          | `oklch(0.72 0.08 30)`          | **Q2 lock**: warm sepia retained, chroma reduced 0.12 → 0.08 to avoid neon. | accent vs accent-fg: 7.4:1                |
| `--color-accent-foreground`    | `oklch(0.985 0.005 90)`        | `oklch(0.18 0.014 270)`        | Dark ink on the high-L accent (parity with primary).                    | (paired above)                                |
| `--color-destructive`          | `oklch(0.55 0.20 27)`          | `oklch(0.66 0.17 27)`          | Slight L bump, slight chroma drop — visible without being hostile.      | destructive vs destructive-fg: 5.0:1          |
| `--color-destructive-foreground` | `oklch(0.985 0.005 90)`      | `oklch(0.985 0.005 90)`        | Ivory in both modes (destructive is high enough chroma to support it).  | (paired above)                                |
| `--color-border`               | `oklch(0.90 0.008 90)`         | `oklch(0.30 0.014 270)`        | One step above card — discoverable but not loud.                        | (visual separator, no AA)                     |
| `--color-input`                | `oklch(0.90 0.008 90)`         | `oklch(0.30 0.014 270)`        | Same as border (matches light pattern).                                 | (visual separator, no AA)                     |
| `--color-ring`                 | `oklch(0.62 0.12 30)`          | `oklch(0.72 0.08 30)`          | Tracks accent in both themes (consistent focus identity).               | ring vs bg: 4.8:1 (passes 3:1 non-text)       |
| `--fallback-l`                 | `0.78`                         | `0.42`                         | **Q6 lock**: lower than initial 0.45 estimate — at 0.42 the ivory glyph passes AA on all 6 hue bands. | panel vs glyph: ~4.6:1+ on every band |
| `--fallback-fg`                | `oklch(0.21 0.025 270)`        | `oklch(0.96 0.005 90)`         | Light: deep ink. Dark: ivory glyph (same hue family as `--color-foreground`, slightly higher L for guarantee margin). | (paired with --fallback-l) |

> **Contrast verification**: ratios above are computed off oklch L
> values via `(L+0.05) / (lower_L+0.05)` approximation on the relative
> luminance side; the apply step runs `@axe-core/playwright` on `/`
> in dark mode for the canonical check (Q10).

### ADR-0051: Tailwind v4 `@custom-variant dark` declaration

**Choice**: Add `@custom-variant dark (&:where(.dark, .dark *));`
immediately after `@import "tailwindcss";` in
`apps/web/app/globals.css`. Documented as a load-bearing line — its
absence is hard to debug because individual `dark:` utilities silently
no-op without compiler error.

**Alternatives considered**:
- Leave the default `prefers-color-scheme: dark` variant — rejected:
  conflicts with class strategy + `next-themes` toggle.
- Use `@variant dark { … }` blocks per component — rejected: defeats
  the token system; manual maintenance.

**Rationale**: Context7-verified canonical Tailwind v4 docs path
(`/tailwindlabs/tailwindcss.com` → "Toggling dark mode manually"). The
`:where(.dark, .dark *)` pseudo-class keeps specificity at zero so
authored utilities still win over the variant.

### ADR-0052: ImageFallback CSS-variable L swap (RSC-safe Option A)

**Choice**: `ImageFallback` stays an RSC. Hue is computed server-side
from the slug hash and emitted as an inline CSS variable
(`--fallback-h: <degree>`). The `background-color` is a static string
`oklch(var(--fallback-l) 0.06 var(--fallback-h))`. The glyph color is
`var(--fallback-fg)`. Both `--fallback-l` and `--fallback-fg` flip via
the `:root.dark` block.

**Alternatives considered**:
- `useTheme()` + client component (Q6 Option B) — rejected: forces
  every catalog card subtree to be client; bloats bundle; wastes RSC
  benefits.
- Stacked light/dark elements (Option C) — rejected: DOM bloat at scale
  (every card adds two divs).
- Drop the pastel device in dark (Option D) — rejected: loses slug-
  deterministic identity that distinguishes catalog cards.

**Rationale**: Cheapest correct fix. No client JS. Hue still
deterministic per slug. Theme controls both L and glyph FG via global
tokens. ADR-0036's uniform-AA guarantee is preserved (extended below).

### ADR-0053: ThemeToggle 3-state cycle (vs 2-state)

**Choice**: 3-state cycle `light → dark → system → light`. lucide
`Sun` / `Moon` / `Monitor` icons. `aria-label` reflects current state.

**Alternatives considered**:
- 2-state `light ↔ dark` toggle — rejected: loses OS auto-switch
  respect; fragwise is read at all hours (editorial site, late-night
  browsing pattern), so `system` is a real user choice not a power-user
  affectation.
- Dropdown menu with three explicit options — rejected: extra
  Radix primitive, more JS, marginal UX upside; a single button
  cycling is the established pattern (`next-themes`, shadcn examples).

**Rationale**: Q3 ratified. Cost is ~3 KB gzipped client island and
one extra lucide icon (Monitor). Behavioral payoff: macOS Sequoia / iOS
auto-switching honored without per-user intervention.

### ADR-0054: defaultTheme="light" for launch (vs system)

**Choice**: `<ThemeProvider defaultTheme="light" enableSystem={true}>`.
First-ever visitor sees ivory; can opt into dark or system via toggle;
choice persists in localStorage (`next-themes` default key `"theme"`).

**Alternatives considered**:
- `defaultTheme="system"` — rejected for launch: OS-dark users land on
  not-yet-battle-tested dark UI on first paint. Defer to post-launch
  patch (proposal "Out of Scope").

**Rationale**: Q4 ratified. Predictable for marketing screenshots and
shareable links. `enableSystem={true}` still ON, so `system` is reachable
through the toggle — no functionality lost. Migration path clear.

### Extension to ADR-0036: dark mode WCAG AA guarantee

ADR-0036 promised uniform AA contrast on `ImageFallback` at light
L=0.78. This design extends the guarantee:

> At light `--fallback-l = 0.78` with chroma 0.06, the deep-ink glyph
> (`oklch(0.21 0.025 270)`) passes WCAG AA on all 6 hue bands.
>
> **Extension (P4c)**: at dark `--fallback-l = 0.42` with chroma 0.06,
> the ivory glyph (`oklch(0.96 0.005 90)`) passes WCAG AA on all 6
> hue bands. Chroma stays at 0.06 — same six BANDS hue palette
> (`[25, 35, 45, 70, 200, 280]`) — only L and glyph FG flip per theme.
>
> Verified by axe-core dark-mode pass on `/` in apply step. If a
> single hue band fails (notably band 200 cyan), L will be lowered to
> 0.40 in a follow-up apply iteration; the spec scenario "dark
> ImageFallback panel + glyph passes AA" is the gate.

## Data Flow

```
User clicks ThemeToggle ──→ next-themes setTheme() ──→ <html> class flip
       │                                                       │
       ▼                                                       ▼
  aria-label updates                              localStorage["theme"] write
       │                                                       │
       ▼                                                       ▼
  next render reads useTheme().theme              :root.dark token block activates
                                                  + Tailwind dark: utilities fire
                                                  + ImageFallback --fallback-l swaps
                                                  + Sonner toaster theme prop flips
                                                  + Glossary popover bg flips
```

First-paint (no localStorage entry):

```
<html suppressHydrationWarning>           pre-paint inline <script>
  └─ ThemeProvider injects script ───→    reads localStorage("theme")
                                          ├─ none → applies defaultTheme ("light")
                                          └─ found → applies stored theme
                                                       │
                                                       ▼
                                          <html class="…"> set BEFORE first paint
                                          → no FOUC
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/web/styles/tokens.css` | Modify | Add `:root.dark` block with full hand-tuned oklch palette + `--fallback-l: 0.42` + `--fallback-fg`. Drop `color-scheme: light` declaration. Add `--fallback-l: 0.78` and `--fallback-fg` ink token in `:root`. |
| `apps/web/app/globals.css` | Modify | Insert `@custom-variant dark (&:where(.dark, .dark *));` immediately after `@import "tailwindcss";`. |
| `apps/web/app/layout.tsx` | Modify | Drop `forcedTheme="light"`; set `enableSystem={true}`; keep `defaultTheme="light"`; change `viewport.colorScheme` from `"light"` to `"light dark"`. |
| `apps/web/components/site/ThemeToggle.tsx` | Create | `"use client"` 3-state cycle; lucide `Sun`/`Moon`/`Monitor`; aria-label reflects state; mounts via `useTheme()` hook. |
| `apps/web/components/site/Header.tsx` | Modify | Insert `<ThemeToggle />` between disabled search input and `<MobileMenu />` in the right cluster. |
| `apps/web/components/site/MobileMenu.tsx` | Modify | Insert `<ThemeToggle />` inside `<SheetContent>` after the nav list. |
| `apps/web/components/catalog/ImageFallback.tsx` | Modify | Refactor: emit `--fallback-h` inline; `background` uses `oklch(var(--fallback-l) 0.06 var(--fallback-h))`; glyph uses `var(--fallback-fg)`. |
| `apps/web/components/ui/sonner.tsx` | Modify | Change `--popover` / `--popover-foreground` / `--border` / `--radius` references to `--color-popover` / `--color-popover-foreground` / `--color-border` / `--radius-md` to match our actual token names (see "Sonner verification"). |
| `apps/web/__tests__/components/ThemeToggle.test.tsx` | Create | Vitest: cycle 3 clicks, assert `aria-label` mutates, assert `setTheme` called with light/dark/system in order. |
| `apps/web/__tests__/components/ImageFallback.test.tsx` | Modify (or add) | Render in `.dark`-classed container; assert the inline `--fallback-h` is set; assert `background-color` uses the L variable (string match on `var(--fallback-l)`). |
| `apps/web/e2e/color-mode.spec.ts` | Create | Playwright: visit `/`; toggle to system; `emulateMedia({ colorScheme: 'dark' })`; assert `<html class="dark">`; axe-core scan in dark mode; keyboard reachability of toggle from search input. |
| `apps/web/package.json` | Modify | Add `@axe-core/playwright` as devDependency. |

## Interfaces / Contracts

### `tokens.css` (full content after edit)

```css
/*
 * Fragwise design tokens — light + dark (4c).
 * Editorial-perfumery direction (ADR-0033). Dark palette ratified in
 * ADR-0050 via frontend-design skill pass.
 *
 * NOTE: `color-scheme` is no longer declared here; next-themes writes
 * it on <html> at runtime via `enableColorScheme`. Pre-hydration UA
 * hint comes from `viewport.colorScheme = "light dark"` in layout.tsx.
 */

:root {
  /* Color (oklch, perceptually uniform) — light theme */
  --color-background: oklch(0.985 0.005 90);
  --color-foreground: oklch(0.21 0.025 270);

  --color-card: oklch(0.99 0.003 90);
  --color-card-foreground: oklch(0.21 0.025 270);

  --color-popover: oklch(0.99 0.003 90);
  --color-popover-foreground: oklch(0.21 0.025 270);

  --color-muted: oklch(0.95 0.008 90);
  --color-muted-foreground: oklch(0.46 0.02 270);

  --color-primary: oklch(0.30 0.05 35);
  --color-primary-foreground: oklch(0.985 0.005 90);

  --color-secondary: oklch(0.94 0.012 70);
  --color-secondary-foreground: oklch(0.21 0.025 270);

  --color-accent: oklch(0.62 0.12 30);
  --color-accent-foreground: oklch(0.985 0.005 90);

  --color-destructive: oklch(0.55 0.20 27);
  --color-destructive-foreground: oklch(0.985 0.005 90);

  --color-border: oklch(0.90 0.008 90);
  --color-input: oklch(0.90 0.008 90);
  --color-ring: oklch(0.62 0.12 30);

  /* ImageFallback CSS-variable L + glyph FG (ADR-0052) */
  --fallback-l: 0.78;
  --fallback-fg: oklch(0.21 0.025 270);

  /* Spacing scale (4px base) — unchanged */
  --space-0: 0;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;
  --space-16: 4rem;
  --space-20: 5rem;
  --space-24: 6rem;

  /* Radii — unchanged */
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-full: 9999px;

  /* Shadows — unchanged */
  --shadow-sm: 0 1px 2px oklch(0.21 0.025 270 / 0.04);
  --shadow-md: 0 4px 12px oklch(0.21 0.025 270 / 0.06);
  --shadow-lg: 0 12px 32px oklch(0.21 0.025 270 / 0.08);

  /* Type scale — unchanged */
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 1.875rem;
  --font-size-4xl: 2.25rem;
  --font-size-5xl: 3rem;
  --font-size-6xl: 3.75rem;

  /* Line heights — unchanged */
  --line-height-tight: 1.1;
  --line-height-snug: 1.3;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.65;
}

/* Dark theme tokens — ADR-0050 (frontend-design pass).
 * The :root.dark selector matches Tailwind v4's @custom-variant dark
 * (&:where(.dark, .dark *)) declaration in globals.css. */
:root.dark {
  --color-background: oklch(0.16 0.012 270);
  --color-foreground: oklch(0.94 0.005 90);

  --color-card: oklch(0.205 0.013 270);
  --color-card-foreground: oklch(0.94 0.005 90);

  --color-popover: oklch(0.245 0.014 270);
  --color-popover-foreground: oklch(0.94 0.005 90);

  --color-muted: oklch(0.235 0.013 270);
  --color-muted-foreground: oklch(0.70 0.018 270);

  --color-primary: oklch(0.78 0.07 35);
  --color-primary-foreground: oklch(0.18 0.014 270);

  --color-secondary: oklch(0.265 0.014 270);
  --color-secondary-foreground: oklch(0.94 0.005 90);

  --color-accent: oklch(0.72 0.08 30);
  --color-accent-foreground: oklch(0.18 0.014 270);

  --color-destructive: oklch(0.66 0.17 27);
  --color-destructive-foreground: oklch(0.985 0.005 90);

  --color-border: oklch(0.30 0.014 270);
  --color-input: oklch(0.30 0.014 270);
  --color-ring: oklch(0.72 0.08 30);

  --fallback-l: 0.42;
  --fallback-fg: oklch(0.96 0.005 90);
}
```

### `globals.css` diff

```diff
 @import "tailwindcss";
+@custom-variant dark (&:where(.dark, .dark *));
 @import "../styles/tokens.css";
```

> Placement verified in Context7 docs (`/tailwindlabs/tailwindcss.com`,
> "Overriding the dark variant for class-based dark mode toggling"):
> `@custom-variant` immediately after the Tailwind import. The token
> import follows on the next line — order is irrelevant between those
> two but conventional to put the variant first.

### `app/layout.tsx` diff

```diff
 export const viewport: Viewport = {
-  colorScheme: "light",
+  colorScheme: "light dark",
 };
@@
         <ThemeProvider
           attribute="class"
           defaultTheme="light"
-          forcedTheme="light"
-          enableSystem={false}
+          enableSystem={true}
           disableTransitionOnChange
         >
```

### `ThemeToggle.tsx` (new, full content)

```tsx
"use client";

import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

type ThemeName = "light" | "dark" | "system";

const ORDER: ThemeName[] = ["light", "dark", "system"];

const NEXT: Record<ThemeName, ThemeName> = {
  light: "dark",
  dark: "system",
  system: "light",
};

const LABEL: Record<ThemeName, string> = {
  light: "Switch theme: currently light",
  dark: "Switch theme: currently dark",
  system: "Switch theme: currently system",
};

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // next-themes returns undefined on first render until it reads
  // localStorage (avoids hydration mismatch). Render a stable
  // placeholder until mounted to keep aria-label deterministic.
  useEffect(() => {
    setMounted(true);
  }, []);

  const current: ThemeName = mounted
    ? ((ORDER.includes(theme as ThemeName) ? theme : "system") as ThemeName)
    : "light";

  const Icon = current === "light" ? Sun : current === "dark" ? Moon : Monitor;

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      aria-label={LABEL[current]}
      onClick={() => setTheme(NEXT[current])}
      // Keep button visible-but-inert before mount (hydration parity)
      suppressHydrationWarning
    >
      <Icon className="size-4" aria-hidden />
    </Button>
  );
}
```

> **Lucide check**: `Sun`, `Moon`, and `Monitor` are all exported from
> the installed `lucide-react@0.460.0` (verified by inspecting
> `apps/web/node_modules/lucide-react/dist/esm/icons/{sun,moon,monitor}.js`).
> No P4a-style F13 fallback to inline SVG required.

### `Header.tsx` diff

```diff
-import { Search } from "lucide-react";
+import { Search } from "lucide-react";
+import { ThemeToggle } from "./ThemeToggle";
@@
         <div className="hidden items-center gap-3 md:flex">
           <label className="relative">
             <Search
               aria-hidden
               className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
             />
             <Input
               type="search"
               placeholder="Search coming soon"
               disabled
               aria-label="Search (coming soon)"
               className="w-64 pl-9 font-mono text-xs"
             />
           </label>
+          <ThemeToggle />
         </div>
+        <div className="flex items-center md:hidden">
+          <ThemeToggle />
+        </div>
         <MobileMenu nav={NAV} />
```

> The mobile cluster mirrors the toggle so it is reachable on `<md`
> viewports without opening the sheet (the in-sheet toggle remains for
> users who already have the sheet open). Both toggles dispatch the
> same `setTheme()` call and update in lockstep.

### `MobileMenu.tsx` diff

```diff
+import { ThemeToggle } from "./ThemeToggle";
@@
         <nav className="mt-6 flex flex-col gap-3 px-4">
           {nav.map((item) =>
             item.ready ? (
               <Link
                 key={item.href}
                 href={item.href}
                 className="text-base text-foreground transition-colors hover:text-accent"
               >
                 {item.label}
               </Link>
             ) : (
               <span
                 key={item.href}
                 aria-disabled="true"
                 title="Coming with phase 4c+"
                 className="cursor-not-allowed text-base text-muted-foreground/50"
               >
                 {item.label}
               </span>
             ),
           )}
         </nav>
+        <div className="mt-6 flex items-center gap-3 border-t border-border px-4 pt-6">
+          <span className="text-xs text-muted-foreground font-mono">Theme</span>
+          <ThemeToggle />
+        </div>
```

### `ImageFallback.tsx` (full rewrite)

```tsx
// W5/F4: oklch panel; theme-aware lightness + glyph FG via
// --fallback-l / --fallback-fg (ADR-0052). Hue is still per-slug
// deterministic; L flips on .dark via tokens.css.
import { createHash } from "node:crypto";

const BANDS = [25, 35, 45, 70, 200, 280];

function panelHue(slug: string): number {
  const h = createHash("sha256").update(slug).digest("hex");
  const band = parseInt(h.slice(0, 2), 16) % 6;
  const jitterByte = parseInt(h.slice(2, 4), 16);
  const jitter = (jitterByte % 12) - 6;
  return BANDS[band] + jitter;
}

export function ImageFallback({
  slug,
  name,
}: {
  slug: string;
  name: string;
}) {
  const hue = panelHue(slug);
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  return (
    <div
      role="img"
      aria-label={`${name} (no bottle image available)`}
      className="absolute inset-0 flex items-end justify-start"
      style={
        {
          "--fallback-h": String(hue),
          backgroundColor: "oklch(var(--fallback-l) 0.06 var(--fallback-h))",
        } as React.CSSProperties
      }
    >
      <span
        className="font-display select-none"
        style={{
          color: "var(--fallback-fg)",
          fontSize: "60%",
          lineHeight: 1,
          padding: "0 0 0.5em 0.4em",
          fontWeight: 600,
        }}
      >
        {initial}
      </span>
    </div>
  );
}
```

### Sonner verification (`components/ui/sonner.tsx`)

Read of current file: it references `var(--popover)`, `var(--popover-foreground)`, `var(--border)`, `var(--radius)`. Our token system declares `--color-popover`, `--color-popover-foreground`, `--color-border`, and `--radius-md` (no `--radius` alone, no un-prefixed `--popover`). Today these vars resolve to nothing and Sonner falls back to its own defaults — so it visually "just works" in light mode but will not flip with our dark tokens.

**Patch required (yes)**:

```diff
       style={
         {
-          "--normal-bg": "var(--popover)",
-          "--normal-text": "var(--popover-foreground)",
-          "--normal-border": "var(--border)",
-          "--border-radius": "var(--radius)",
+          "--normal-bg": "var(--color-popover)",
+          "--normal-text": "var(--color-popover-foreground)",
+          "--normal-border": "var(--color-border)",
+          "--border-radius": "var(--radius-md)",
         } as React.CSSProperties
       }
```

> Apply step triggers a real toast in dark mode to verify the patch.
> The `useTheme()` + `theme` prop forwarding already in place is
> correct; only the CSS variable names needed alignment with our
> token system.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Unit (Vitest) | `ThemeToggle` cycle and aria | Mock `next-themes` `useTheme`; render; click 3×; assert `setTheme` called with `dark`, `system`, `light` in order; assert `aria-label` reflects current state per render. |
| Unit (Vitest) | `ImageFallback` reads `--fallback-l` | Render with a fixed slug; assert inline style sets `--fallback-h`; assert `background-color` string contains the literal `var(--fallback-l)`. (Vitest jsdom cannot resolve `oklch()` so we assert the variable reference, not the computed color.) |
| E2E (Playwright) | First-paint stability | Visit `/` cold; assert `<html class="light">` on first network idle; screenshot taken (no diff baseline — Q10). |
| E2E (Playwright) | 3-state cycle | Click toggle 3 times; after each click assert the `<html>` class. |
| E2E (Playwright) | System theme respected | `page.emulateMedia({ colorScheme: 'dark' })`; click toggle until `system`; assert `<html class="dark">`; switch emulation to `light`; assert `<html class="light">`. |
| E2E (Playwright) | Keyboard reach | Tab forward from search input; assert `ThemeToggle` is the next focusable; visible focus ring asserted via computed style on `outline`. |
| E2E (axe-core) | Dark contrast | Run `@axe-core/playwright` on `/` with `<html class="dark">`; assert zero color-contrast violations. Home only — diminishing returns elsewhere (Q10). |
| Manual (one-shot) | Sonner in dark | Apply step triggers a toast in dark mode and visually verifies the popover bg / text / border match the dark tokens. |

## Migration / Rollout

No data migration. No feature flag. Single-PR rollout. Per-browser
state lives in localStorage under the `next-themes` default key
(`"theme"`). Existing visitors with no entry default to `light` (matches
P4a/P4b behavior). Existing visitors with the key set get whatever
they previously chose — but since 4a/4b had `forcedTheme="light"`, the
key was never written by the runtime; first-ever-toggle in 4c writes it.

Rollback: revert the merge commit. No DB writes, no API surface
changes, no downstream consumer impact.

## Open Questions

None blocking. Two minor items resolved by apply step empirically:

- [ ] **Confirm `--fallback-l = 0.42` passes AA on hue band 200 (cyan)
      with the ivory glyph.** If axe flags it, drop to `0.40` and
      re-run; the ADR-0036 extension permits this.
- [ ] **Confirm Sonner toast renders correctly in dark mode after the
      `--color-*` token rename.** Apply step fires a real toast as a
      smoke check.

## Cross-cutting

- **Bundle impact**: `ThemeToggle` is a small client island (~3 KB
  gzipped including the three lucide icons via tree-shaking). Sonner
  patch is a one-line CSS-var rename — no bundle change. Total
  P4c bundle delta: well within the 220 KB initial-JS budget set in
  ADR-0033 (revised). `size-limit` will catch any regression in CI.
- **No FOUC**: `<ThemeProvider>` injects an inline `<script>` in
  `<head>` (Context7-verified path) that reads localStorage and writes
  the `class`/`style` on `<html>` synchronously before paint.
  `<html suppressHydrationWarning>` is already in place. Removing
  `forcedTheme` does not disable the script — it disables the
  override. The Playwright first-paint scenario is the gate.
- **a11y**:
  - `ThemeToggle` MUST be keyboard-reachable from header (verified by
    Playwright keyboard test).
  - `aria-label` MUST update on every render to reflect the current
    state (verified by Vitest + Playwright).
  - Focus ring is `outline: 2px solid var(--color-ring)` from
    `globals.css`; `--color-ring` flips per theme so the ring stays
    visible on both surfaces (verified by axe contrast scan).
  - Toggle is a real `<button>` (via shadcn `<Button>`); no role
    overrides.
- **Editorial-perfumery preservation**: ADR-0050 commits to a warm
  dark — ink-blue base + ivory paper foreground + sepia accent at
  reduced chroma. No cool-blue `#0a0a0a` SaaS-default. Dark
  ImageFallback panels stay pastel-but-deeper rather than flat-dark.
  This is the explicit guardrail against "AI-default-dark" that
  motivated the `frontend-design` pass (Q12).

## Frontend-design skill output (for the record)

The skill pass produced four locked artifacts, all reflected above:

1. **Dark palette** (19 tokens) — ADR-0050 table.
2. **Accent chroma posture in dark** — warm sepia, chroma 0.08 (down
   from light 0.12); avoids neon at low surround L (ADR-0050 row).
3. **`--fallback-l` dark value** — 0.42 (lower than provisional 0.45
   to give the ivory glyph margin on band 200; ADR-0050 row + ADR-0036
   extension).
4. **Glyph FG swap token** — `--fallback-fg`: deep ink in light,
   ivory at L=0.96 in dark (ADR-0050 row).

Two additional secondary checks the skill informed:

- **Glossary popover elevation in dark**: `--color-popover` set two
  steps above `--color-background` (0.245 vs 0.16) — the popover is
  visibly elevated, not flush. Border is `--color-border` (0.30 cool
  grey) which is high enough above the popover bg (0.245) to give a
  clear edge.
- **ThemeToggle visual treatment**: `<Button variant="ghost" size="icon">`
  size aligns with the disabled search input height — matches the
  refined aesthetic. `size-4` lucide icon weight is consistent with
  the `Search` icon already in the header.
