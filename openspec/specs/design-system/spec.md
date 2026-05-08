# design-system Specification

## Purpose

Defines the visual foundation of `apps/web/`: design tokens, font configuration, theme provider wiring, and the inventory of shadcn/ui primitives required by Phase 4a. Aesthetic finalization (palette values, exact font weights, hierarchy) is delegated to the `frontend-design` skill at `sdd-design`; this spec only locks the contract.

## Requirements

### Requirement: Display, Body, And Mono Fonts Loaded Via next/font

The web app MUST load three Google Fonts via `next/font/google` from `apps/web/app/layout.tsx`: Fraunces (display), Manrope (sans body), and JetBrains Mono (technical labels). Each font MUST be exposed as a CSS variable consumable by Tailwind v4 token mapping. `display: 'swap'` MUST be set; `subsets` MUST include `latin`. The previous `Inter` font import MUST be removed.

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

### Requirement: CSS Token File With Light Theme Variables

A token file (e.g., `apps/web/styles/tokens.css` or `apps/web/app/globals.css`) MUST define CSS custom properties for: color (`--color-primary`, `--color-secondary`, `--color-accent`, `--color-muted`, `--color-foreground`, `--color-background`, `--color-card`, `--color-border`, `--color-ring`), spacing scale, radii, shadows, and font sizes. Light theme tokens MUST be defined under the `:root` selector. Dark theme tokens MUST NOT be defined in Phase 4a.

#### Scenario: Required color tokens present

- GIVEN the token CSS file
- WHEN parsing CSS custom properties under `:root`
- THEN every required `--color-*` token, at least one `--radius-*`, at least one `--shadow-*`, and at least one font-size token is defined

#### Scenario: Dark theme deliberately absent in 4a

- GIVEN `apps/web/`
- WHEN searching for a `[data-theme="dark"]` or `.dark { ... }` selector with token definitions
- THEN no such selector exists in 4a's committed CSS

### Requirement: Theme Provider Wired With Light-Only Mode

`apps/web/components/theme-provider.tsx` MUST exist and be rendered as a wrapper inside `app/layout.tsx`. In Phase 4a it MUST be configured for light-only mode (e.g., `defaultTheme="light"`, `forcedTheme="light"` or equivalent), so that no theme toggle UI affects rendering until 4b.

#### Scenario: Layout wraps children in ThemeProvider

- GIVEN `apps/web/app/layout.tsx`
- WHEN reading the file
- THEN it imports the theme provider from `components/theme-provider`
- AND `{children}` is rendered inside `<ThemeProvider>`
- AND the provider props pin the theme to light

### Requirement: shadcn Primitive Set Extended For Phase 4a

In addition to the 10 primitives shipped in Phase 0b (`button`, `card`, `input`, `label`, `dialog`, `sonner`, `dropdown-menu`, `tabs`, `separator`, `badge`), Phase 4a MUST install: `sheet`, `tooltip`, `accordion`, `command`, `skeleton`, `popover`, `scroll-area`, `breadcrumb`, `select`, and `pagination`. Each MUST be present at `apps/web/components/ui/<name>.tsx`.

#### Scenario: All 20 primitive files present

- GIVEN `apps/web/components/ui/`
- WHEN listing the directory
- THEN one `.tsx` file exists for each of: `button`, `card`, `input`, `label`, `dialog`, `sonner`, `dropdown-menu`, `tabs`, `separator`, `badge`, `sheet`, `tooltip`, `accordion`, `command`, `skeleton`, `popover`, `scroll-area`, `breadcrumb`, `select`, `pagination`

### Requirement: Tailwind v4 Content Auto-Detection Covers New Source Roots

Tailwind v4's content auto-detection MUST cover `apps/web/components/ui/`, `apps/web/components/site/`, `apps/web/components/catalog/`, and `apps/web/app/`. Class names emitted from any of these directories MUST NOT be purged by `next build`.

#### Scenario: Classes from each source root survive build

- GIVEN a class like `bg-primary` used in a component under each of the four source roots
- WHEN running `next build`
- THEN the produced CSS contains rules for those classes
- AND no class from those roots is missing from the build output

### Requirement: No CSS-In-JS Libraries In 4a

Phase 4a MUST style components using Tailwind utility classes plus CSS custom properties only. Dependencies on `styled-components`, `@emotion/*`, or `@vanilla-extract/*` MUST NOT be added.

#### Scenario: No CSS-in-JS deps in package.json

- GIVEN `apps/web/package.json`
- WHEN inspecting `dependencies` and `devDependencies`
- THEN no entry matching `styled-components`, `@emotion/*`, or `@vanilla-extract/*` is present

### Requirement: Article Markdown Rendering Stack

`apps/web/package.json` runtime `dependencies` MUST include `react-markdown` at `^9`, `remark-gfm` at `^4`, and `rehype-sanitize` at `^6`. The `<ArticleBody>` component MUST compose them in this order: parse the markdown source, apply GFM extensions via `remark-gfm`, then sanitize the resulting HAST via `rehype-sanitize`. The sanitize schema MUST drop `<script>`, `<iframe>`, and any `on*` event-handler attributes; it MUST allow common formatting (headings, paragraphs, emphasis), code blocks, tables, lists, and links.

#### Scenario: Required deps pinned at major versions

- GIVEN `apps/web/package.json`
- WHEN parsing it as JSON
- THEN `dependencies` contains `react-markdown` matching `^9`
- AND `dependencies` contains `remark-gfm` matching `^4`
- AND `dependencies` contains `rehype-sanitize` matching `^6`

#### Scenario: ArticleBody pipeline order

- GIVEN the `<ArticleBody>` component source
- WHEN inspecting its plugin configuration
- THEN `remark-gfm` is registered as a remark plugin
- AND `rehype-sanitize` is registered as a rehype plugin AFTER any rehype transformations
- AND the sanitize schema explicitly disallows `script`, `iframe`, and `on*` attributes

#### Scenario: Sanitize schema allows common formatting

- GIVEN markdown input containing a heading, a code fence, a table, a list, and a link
- WHEN `<ArticleBody>` renders the input
- THEN the output contains `<h1>`/`<h2>`, `<pre><code>`, `<table>`, `<ul>`/`<ol>`, and `<a>` elements
- AND the link element carries the `rel="noopener noreferrer"` and `target="_blank"` attributes
