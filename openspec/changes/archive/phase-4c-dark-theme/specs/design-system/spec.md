# Delta for design-system

## MODIFIED Requirements

### Requirement: CSS Token File With Light And Dark Theme Variables

A token file (`apps/web/styles/tokens.css`) MUST define CSS custom properties for color, spacing scale, radii, shadows, and font sizes. Light theme tokens MUST be defined under the `:root` selector. Dark theme tokens MUST be defined under the `:root.dark` (or equivalent `.dark`) selector.

Each palette MUST cover the following color tokens (paired with their `*-foreground` counterparts where applicable): `--color-background`, `--color-foreground`, `--color-card`, `--color-card-foreground`, `--color-popover`, `--color-popover-foreground`, `--color-primary`, `--color-primary-foreground`, `--color-secondary`, `--color-secondary-foreground`, `--color-muted`, `--color-muted-foreground`, `--color-accent`, `--color-accent-foreground`, `--color-destructive`, `--color-destructive-foreground`, `--color-border`, `--color-input`, and `--color-ring`. Each palette MUST also define `--fallback-l` (CSS variable consumed by `ImageFallback`).

All token color values MUST use the `oklch()` color space. The dark accent MUST stay in the warm sepia hue family with reduced chroma compared to its light counterpart (per ADR-0033 brand guardrail).

`tokens.css` MUST NOT contain a `color-scheme: light` declaration; runtime `color-scheme` is managed by `next-themes` via its inline style on `<html>`.

(Previously: spec asserted "Dark theme tokens MUST NOT be defined" and "Dark theme deliberately absent in 4a"; light-only token block at `:root` only.)

#### Scenario: Required color tokens present in light theme

- GIVEN the token CSS file
- WHEN parsing CSS custom properties under `:root`
- THEN every required `--color-*` token, at least one `--radius-*`, at least one `--shadow-*`, and at least one font-size token is defined
- AND `--fallback-l` is defined

#### Scenario: Dark theme tokens present under .dark selector

- GIVEN the token CSS file
- WHEN parsing CSS custom properties under `:root.dark` (or `.dark`)
- THEN every required `--color-*` token from the light palette has a dark counterpart
- AND `--fallback-l` resolves to a value distinct from the light value

#### Scenario: Background token resolves per active theme class

- GIVEN a document with `<html class="dark">`
- WHEN computed style for `--background` is read on `<body>`
- THEN it resolves to the dark oklch value
- AND when the `dark` class is removed, it resolves to the ivory light oklch value

#### Scenario: All token color values use oklch

- GIVEN both `:root` and `:root.dark` token blocks
- WHEN scanning every `--color-*` declaration
- THEN every value uses the `oklch()` function

#### Scenario: Dark accent stays in warm sepia hue family

- GIVEN the `--color-accent` token under `:root.dark`
- WHEN inspecting its oklch hue component
- THEN the hue is in the warm sepia range (consistent with the light theme accent hue)
- AND the chroma is lower than the light theme `--color-accent` chroma

#### Scenario: color-scheme declaration removed from tokens

- GIVEN `apps/web/styles/tokens.css`
- WHEN searching the file for the literal `color-scheme:`
- THEN no occurrence is present

### Requirement: Display, Body, And Mono Fonts Loaded Via next/font

The web app MUST load three Google Fonts via `next/font/google` from `apps/web/app/layout.tsx`: Fraunces (display), Manrope (sans body), and JetBrains Mono (technical labels). Each font MUST be exposed as a CSS variable consumable by Tailwind v4 token mapping. `display: 'swap'` MUST be set; `subsets` MUST include `latin`. The previous `Inter` font import MUST be removed.

(Previously: identical contract; preserved verbatim across phase 4c — included in this REPLACED block only because it sat alongside the now-modified token requirement during canonical merge.)

#### Scenario: Three font families loaded with CSS variables

- GIVEN `apps/web/app/layout.tsx`
- WHEN reading the file
- THEN it imports `Fraunces`, `Manrope`, and `JetBrains_Mono` from `next/font/google`
- AND each declares `display: 'swap'` and a `variable` (e.g., `--font-display`, `--font-sans`, `--font-mono`)
- AND no import of `Inter` remains

#### Scenario: Font variables wired through Tailwind v4 theme mapping

- GIVEN `apps/web/app/globals.css` (or a token file imported by it)
- WHEN inspecting the `@theme` block
- THEN `--font-display`, `--font-sans`, and `--font-mono` are mapped to the three font CSS variables
- AND `next build` emits HTML where headings use the display font and body uses the sans font

## ADDED Requirements

### Requirement: Tailwind V4 Dark Variant Declaration

`apps/web/app/globals.css` MUST include the declaration `@custom-variant dark (&:where(.dark, .dark *));` at top-level (after `@import "tailwindcss";`). Without this declaration, Tailwind v4 binds the `dark:` variant to `prefers-color-scheme: dark` and all `dark:` utilities authored against the class strategy silently no-op.

#### Scenario: Custom variant declaration present in globals

- GIVEN `apps/web/app/globals.css`
- WHEN reading the file
- THEN it contains the literal line `@custom-variant dark (&:where(.dark, .dark *));`
- AND the line appears after the Tailwind v4 import directive

#### Scenario: dark utilities fire when .dark class is on ancestor

- GIVEN a built CSS bundle from `next build`
- WHEN inspecting rules generated by a `dark:bg-card` utility
- THEN a rule scoped to `.dark` (or its `:where()` form) is present
- AND visiting a page with `<html class="dark">` applies the rule to elements using that utility

### Requirement: ImageFallback Dark Mode L Swap

`apps/web/components/catalog/ImageFallback.tsx` MUST compute its panel background as `oklch(var(--fallback-l) 0.06 var(--fallback-h))` (the per-instance hue is emitted as an inline custom property; the lightness is read from the global token).

`--fallback-l` MUST be defined in `tokens.css` as `0.78` under `:root` and `0.45` under `:root.dark` (exact dark L subject to ratification by `frontend-design`; default 0.45 reflects the proposal). The foreground glyph color MUST also swap between themes via a CSS variable so that the glyph contrast against the panel passes WCAG AA in both modes (dark ink on light pastel in light theme; light ivory on darker panel in dark theme).

#### Scenario: Panel reads --fallback-l from active theme

- GIVEN an `ImageFallback` instance with an arbitrary slug
- WHEN rendered inside a light document
- THEN the computed `background-color` resolves with `--fallback-l = 0.78`
- AND when rendered inside `<html class="dark">`, it resolves with `--fallback-l = 0.45`

#### Scenario: Hue varies per slug, lightness varies per theme

- GIVEN two `ImageFallback` instances with different slugs in the same theme
- WHEN comparing their inline styles
- THEN their `--fallback-h` values differ
- AND their resolved `--fallback-l` values are identical

#### Scenario: Foreground glyph contrast preserved in both themes

- GIVEN the foreground glyph color uses a CSS variable that flips between themes
- WHEN rendered in light mode
- THEN the glyph color is the deep-ink foreground token (high contrast on the L=0.78 panel)
- AND when rendered in dark mode, the glyph color is the ivory/high-L token (high contrast on the L=0.45 panel)

#### Scenario: Vitest snapshots different resolved L per theme

- GIVEN a Vitest test that renders `ImageFallback` with a fixed slug
- WHEN the test toggles the `.dark` class on the document element and reads computed styles
- THEN the resolved `--fallback-l` value differs between the two states
