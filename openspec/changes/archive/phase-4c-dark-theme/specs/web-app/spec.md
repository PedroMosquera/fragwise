# Delta for web-app

## MODIFIED Requirements

### Requirement: Site Layout With Header, Footer, Drawer, Skip-To-Content

`apps/web/app/(site)/layout.tsx` MUST render the `Header` (with disabled search input), the `Footer`, a mobile `sheet` drawer for navigation, and a `SkipToContent` link as the first focusable element targeting `#main-content`.

The `Header` MUST include the `<ThemeToggle />` client island between the disabled search input and the `MobileMenu` trigger (or in the equivalent right-cluster position on desktop). The `MobileMenu` sheet MUST also include a `<ThemeToggle />` so mobile users can toggle theme without re-opening the drawer.

(Previously: layout shipped Header with disabled search + MobileMenu only; no theme toggle anywhere in chrome.)

#### Scenario: Layout structure present

- GIVEN any page under the `(site)` route group
- WHEN the page renders
- THEN the DOM contains the skip link, header, main content with `id="main-content"`, and footer
- AND on viewports `<md` the nav opens via the sheet drawer

#### Scenario: Header includes the ThemeToggle in the right cluster

- GIVEN the `(site)` layout renders on a desktop viewport
- WHEN inspecting the header DOM
- THEN a `<ThemeToggle />` element is present between the disabled search input and the `MobileMenu` trigger
- AND tabbing forward from the search input reaches the toggle before the mobile menu trigger

#### Scenario: MobileMenu sheet includes the ThemeToggle

- GIVEN the `MobileMenu` sheet is opened on a `<md` viewport
- WHEN inspecting the sheet content
- THEN a `<ThemeToggle />` element is present inside the sheet
- AND it is reachable by keyboard while the sheet is open

### Requirement: Theme Provider Wired With Light Default And System Support

`apps/web/components/theme-provider.tsx` MUST exist and be rendered as a wrapper inside `app/layout.tsx`. It MUST be configured with `attribute="class"`, `defaultTheme="light"`, `enableSystem={true}`, and `disableTransitionOnChange`. The `forcedTheme` prop MUST NOT be set.

`apps/web/app/layout.tsx` MUST set `viewport.colorScheme = "light dark"`. The `metadata.other["color-scheme"]` field MUST NOT be set (runtime `color-scheme` is managed by `next-themes`).

(Previously: provider was pinned to `forcedTheme="light"`, `enableSystem={false}`, and `viewport.colorScheme="light"`, deferring all dark functionality.)

#### Scenario: Layout wraps children in ThemeProvider

- GIVEN `apps/web/app/layout.tsx`
- WHEN reading the file
- THEN it imports the theme provider from `components/theme-provider`
- AND `{children}` is rendered inside `<ThemeProvider>`

#### Scenario: Provider props allow light, dark, and system

- GIVEN the rendered provider
- WHEN inspecting its props
- THEN `attribute === "class"`
- AND `defaultTheme === "light"`
- AND `enableSystem === true`
- AND no `forcedTheme` prop is set

#### Scenario: Viewport colorScheme covers both modes

- GIVEN `apps/web/app/layout.tsx`
- WHEN inspecting the exported `viewport` object
- THEN `colorScheme` is the literal string `"light dark"`
- AND `metadata.other["color-scheme"]` is unset

#### Scenario: html receives class from next-themes script

- GIVEN a fresh visit with no localStorage entry for theme
- WHEN the page hydrates
- THEN `<html>` carries `class="light"` (matching `defaultTheme`)
- AND when the user picks dark via the toggle, `<html>` carries `class="dark"` instead

## ADDED Requirements

### Requirement: Theme Toggle Cycles 3-State

`apps/web/components/site/ThemeToggle.tsx` MUST be a `"use client"` component that uses the `useTheme()` hook from `next-themes`. Activating the toggle MUST cycle the theme in the order light → dark → system → light.

The icon MUST reflect the current selection: lucide `Sun` for `light`, `Moon` for `dark`, `Monitor` for `system`. The element MUST expose an `aria-label` that reflects the current state (e.g., `"Switch theme: currently light"`, `"Switch theme: currently dark"`, `"Switch theme: currently system"`).

State MUST persist across reloads via `next-themes`'s default `localStorage` mechanism (key `"theme"`).

#### Scenario: Three clicks return to original state

- GIVEN the toggle is rendered with current theme `light`
- WHEN the user activates the toggle three times in succession
- THEN after click 1 the theme is `dark`
- AND after click 2 the theme is `system`
- AND after click 3 the theme is `light` again

#### Scenario: Icon and aria-label reflect current theme

- GIVEN the toggle is mounted
- WHEN the current theme is `light`
- THEN the rendered icon is the lucide `Sun` glyph
- AND `aria-label` reads `"Switch theme: currently light"`
- AND when the theme is `dark`, the icon is `Moon` and the label reflects `dark`
- AND when the theme is `system`, the icon is `Monitor` and the label reflects `system`

#### Scenario: Selection persists in localStorage

- GIVEN the user clicks the toggle until the theme is `dark`
- WHEN the page is reloaded
- THEN `localStorage["theme"]` is `"dark"`
- AND the rehydrated page applies `<html class="dark">` before paint

### Requirement: System Theme Respected

When the user's selected theme is `system`, the rendered theme MUST be controlled by the user's OS `prefers-color-scheme` media query. When the OS preference changes while the user has `system` selected, the rendered theme MUST update without a page reload (via the `next-themes` media-query listener).

#### Scenario: System selection follows OS dark preference

- GIVEN the user has selected theme `system`
- AND the test runner emulates `prefers-color-scheme: dark`
- WHEN the page renders
- THEN `<html>` carries `class="dark"`
- AND `useTheme().resolvedTheme` is `"dark"`

#### Scenario: System selection follows OS light preference

- GIVEN the user has selected theme `system`
- AND the test runner emulates `prefers-color-scheme: light`
- WHEN the page renders
- THEN `<html>` carries `class="light"`

#### Scenario: Live OS change updates theme without reload

- GIVEN the user has selected theme `system` and the page is rendered with `class="light"`
- WHEN the OS preference changes to dark and the `prefers-color-scheme` media query fires
- THEN `<html>` updates to `class="dark"` without a navigation or reload

### Requirement: First-Paint Theme Stability

The first visit to any page MUST render in `defaultTheme="light"` without a flash of unstyled content (FOUC) or a brief alternate-theme flash. `next-themes` MUST inject its theme-resolution script before paint so that the `class` attribute on `<html>` is set before any styled content is painted.

#### Scenario: First paint matches default theme

- GIVEN a fresh navigation to `/` with no localStorage entry for `theme`
- WHEN Playwright captures a screenshot at first paint
- THEN the page background color matches the light `--background` token (ivory)
- AND it does not match a transparent or browser-default color
- AND it does not match the dark `--background` token

#### Scenario: No FOUC on hydrated route change

- GIVEN the user has selected theme `dark` and is on `/`
- WHEN navigating client-side to `/fragrances`
- THEN the destination page paints with the dark `--background` token from the first frame
- AND no light-theme flash is observable
